"""Almacenamiento genérico de documentos: LocalStore (demo/pruebas) y FirestoreStore (producción).
Regla de diseño: cada consulta usa filtros de igualdad (o UN solo array_contains/in) para no exigir índices."""
import copy
import glob
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime


def _coincide(doc, filtros):
    for campo, op, valor in filtros:
        v = doc.get(campo)
        if op == "==":
            ok = v == valor
        elif op == "in":
            ok = v in valor
        elif op == "array_contains":
            ok = isinstance(v, list) and valor in v
        else:
            raise ValueError(f"Operador no soportado: {op}")
        if not ok:
            return False
    return True


def _fusionar(base, nuevo):
    """Mezcla profunda de diccionarios (las listas se reemplazan, igual que en Firestore)."""
    for k, v in nuevo.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _fusionar(base[k], v)
        else:
            base[k] = copy.deepcopy(v)
    return base


class LocalStore:
    def __init__(self, ruta=None):
        self._d = {}
        self._ruta = ruta
        self._lock = threading.RLock()
        if ruta and os.path.exists(ruta):
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    self._d = json.load(f)
            except (OSError, ValueError):
                self._d = {}

    def _guardar(self):
        if not self._ruta:
            return
        try:
            with open(self._ruta, "w", encoding="utf-8") as f:
                json.dump(self._d, f, ensure_ascii=False, default=str)
        except OSError:
            pass

    def get(self, col, id):
        with self._lock:
            d = self._d.get(col, {}).get(id)
            return copy.deepcopy(d) if d is not None else None

    def set(self, col, id, data, merge=True):
        with self._lock:
            tabla = self._d.setdefault(col, {})
            if merge and id in tabla:
                _fusionar(tabla[id], data)
            else:
                tabla[id] = copy.deepcopy(data)
            self._guardar()

    def add(self, col, data):
        id = uuid.uuid4().hex[:20]
        self.set(col, id, data, merge=False)
        return id

    def delete(self, col, id):
        with self._lock:
            self._d.get(col, {}).pop(id, None)
            self._guardar()

    def query(self, col, filtros=(), limite=None):
        with self._lock:
            res = []
            for id, doc in self._d.get(col, {}).items():
                if _coincide(doc, filtros):
                    d = copy.deepcopy(doc)
                    d["id"] = id
                    res.append(d)
                    if limite and len(res) >= limite:
                        break
            return res

    def incr(self, col, id, deltas):
        with self._lock:
            doc = self._d.setdefault(col, {}).setdefault(id, {})
            for k, v in deltas.items():
                doc[k] = doc.get(k, 0) + v
            self._guardar()


class SqliteStore:
    """Almacenamiento permanente en un solo archivo (SQLite). Es el predeterminado: no necesita servidor ni cuentas.
    Escribe de forma atómica (no se corrompe si se corta la luz) y hace un respaldo automático por día."""
    persistente = True

    def __init__(self, ruta, respaldos=None, conservar=14):
        self.ruta = ruta
        self.respaldos = respaldos
        self.conservar = conservar
        self._lock = threading.RLock()
        carpeta = os.path.dirname(os.path.abspath(ruta))
        os.makedirs(carpeta, exist_ok=True)
        self._db = sqlite3.connect(ruta, check_same_thread=False, timeout=30)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("CREATE TABLE IF NOT EXISTS docs (col TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL, "
                         "PRIMARY KEY (col, id))")
        self._db.commit()

    # --- lectura / escritura ---
    def _leer(self, col, id):
        r = self._db.execute("SELECT data FROM docs WHERE col=? AND id=?", (col, id)).fetchone()
        return json.loads(r[0]) if r else None

    def _escribir(self, col, id, data):
        self._db.execute("INSERT OR REPLACE INTO docs (col, id, data) VALUES (?,?,?)",
                         (col, id, json.dumps(data, ensure_ascii=False, default=str)))

    def get(self, col, id):
        with self._lock:
            return self._leer(col, id)

    def set(self, col, id, data, merge=True):
        with self._lock:
            actual = self._leer(col, id) if merge else None
            if actual is not None:
                _fusionar(actual, json.loads(json.dumps(data, default=str)))
                data = actual
            self._escribir(col, id, data)
            self._db.commit()

    def add(self, col, data):
        id = uuid.uuid4().hex[:20]
        self.set(col, id, data, merge=False)
        return id

    def delete(self, col, id):
        with self._lock:
            self._db.execute("DELETE FROM docs WHERE col=? AND id=?", (col, id))
            self._db.commit()

    def query(self, col, filtros=(), limite=None):
        with self._lock:
            res = []
            for id, crudo in self._db.execute("SELECT id, data FROM docs WHERE col=?", (col,)):
                doc = json.loads(crudo)
                if _coincide(doc, filtros):
                    doc["id"] = id
                    res.append(doc)
                    if limite and len(res) >= limite:
                        break
            return res

    def incr(self, col, id, deltas):
        with self._lock:
            doc = self._leer(col, id) or {}
            for k, v in deltas.items():
                doc[k] = doc.get(k, 0) + v
            self._escribir(col, id, doc)
            self._db.commit()

    def vacia(self):
        with self._lock:
            return self._db.execute("SELECT 1 FROM docs LIMIT 1").fetchone() is None

    # --- migración desde el archivo JSON de versiones anteriores ---
    def importar_json(self, ruta_json):
        """Copia los datos de un datos_locales.json antiguo. Devuelve cuántos registros pasó."""
        with open(ruta_json, "r", encoding="utf-8") as f:
            datos = json.load(f)
        n = 0
        with self._lock:
            for col, tabla in datos.items():
                for id, doc in (tabla or {}).items():
                    self._escribir(col, id, doc)
                    n += 1
            self._db.commit()
        return n

    # --- respaldo automático ---
    def respaldar(self, destino=None):
        """Copia consistente de la base. Devuelve la ruta creada."""
        destino = destino or self.respaldos
        if not destino:
            return None
        os.makedirs(destino, exist_ok=True)
        nombre = os.path.join(destino, "tutor_" + datetime.now().strftime("%Y-%m-%d_%H%M%S") + ".db")
        with self._lock:
            copia = sqlite3.connect(nombre)
            try:
                self._db.backup(copia)
            finally:
                copia.close()
        for viejo in sorted(glob.glob(os.path.join(destino, "tutor_*.db")))[:-self.conservar]:
            try:
                os.remove(viejo)
            except OSError:
                pass
        return nombre

    def respaldo_diario(self):
        """Hace un respaldo si hoy no se ha hecho ninguno. Nunca interrumpe la app."""
        try:
            if not self.respaldos or self.vacia():
                return None
            hoy = datetime.now().strftime("%Y-%m-%d")
            if glob.glob(os.path.join(self.respaldos, f"tutor_{hoy}_*.db")):
                return None
            return self.respaldar()
        except Exception:
            return None


class FirestoreStore:
    def __init__(self, cuenta):
        import firebase_admin
        from firebase_admin import credentials, firestore
        self._firestore = firestore
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(cuenta))
        self.db = firestore.client()

    def get(self, col, id):
        d = self.db.collection(col).document(id).get()
        return d.to_dict() if d.exists else None

    def set(self, col, id, data, merge=True):
        self.db.collection(col).document(id).set(data, merge=merge)

    def add(self, col, data):
        _, ref = self.db.collection(col).add(data)
        return ref.id

    def delete(self, col, id):
        self.db.collection(col).document(id).delete()

    def query(self, col, filtros=(), limite=None):
        from google.cloud.firestore_v1.base_query import FieldFilter
        q = self.db.collection(col)
        for campo, op, valor in filtros:
            q = q.where(filter=FieldFilter(campo, op, valor))
        if limite:
            q = q.limit(limite)
        res = []
        for d in q.stream():
            x = d.to_dict() or {}
            x["id"] = d.id
            res.append(x)
        return res

    def incr(self, col, id, deltas):
        inc = {k: self._firestore.Increment(v) for k, v in deltas.items()}
        self.db.collection(col).document(id).set(inc, merge=True)


def crear_store(cuenta=None, ruta=None):
    """Firebase si hay credenciales; si no, un archivo en este equipo. Una ruta .json usa el formato antiguo;
    cualquier otra (o ninguna) usa SQLite. Sin ruta, los datos viven solo en memoria (pruebas)."""
    if cuenta:
        return FirestoreStore(cuenta)
    if not ruta:
        return LocalStore()
    if str(ruta).lower().endswith(".json"):
        return LocalStore(ruta)
    almacen = SqliteStore(ruta, respaldos=os.path.join(os.path.dirname(os.path.abspath(ruta)), "respaldos"))
    viejo = os.path.join(os.path.dirname(os.path.abspath(ruta)), "datos_locales.json")
    if almacen.vacia() and os.path.exists(viejo):
        try:
            almacen.importar_json(viejo)
        except (OSError, ValueError):
            pass
    almacen.respaldo_diario()
    return almacen
