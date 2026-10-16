"""Capa de dominio sobre el store genérico. Todas las consultas usan igualdad (sin índices compuestos)."""
import hashlib
import hmac
import re
import secrets as _secrets
import uuid

from . import config, progress, spaced
from .retrieval import normalizar, trocear

PROGRESO_BASE = {"xp": 0, "racha": 0, "mejor_racha": 0, "ultimo_dia": None, "mensajes": 0, "quizzes": 0,
                 "retos": 0, "aciertos": 0, "preguntas": 0, "memoria": "", "dificultades": {}, "dominados": {},
                 "ultimo_tema": None, "xp_msg": {"dia": None, "n": 0}}
COLECCIONES = ["usuarios", "grupos", "progreso", "eventos", "feedback", "alertas", "materiales", "fragmentos",
               "tarjetas", "retos", "avisos", "uso_diario", "uso_global", "config", "encuestas", "errores", "auditoria"]
ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # sin letras ni números que se confundan
CONFIG_DEFECTO = {"tope_global_mensajes": 3000, "meta_semanal_defecto": 100}


def clave(t, n=40):
    """Texto seguro para usar como llave de un mapa."""
    limpio = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(t), flags=re.UNICODE)).strip()
    return limpio[:n].strip() or "general"


def normalizar_codigo(c):
    return re.sub(r"[^A-Z0-9]", "", str(c or "").upper())


def slug(t):
    return re.sub(r"[^a-z0-9]+", "_", str(t).lower()).strip("_") or uuid.uuid4().hex[:8]


class Repo:
    def __init__(self, store):
        self.s = store

    # ---------- usuarios ----------
    def get_usuario(self, uid):
        d = self.s.get("usuarios", uid)
        if d is not None:
            d["uid"] = uid
        return d

    def crear_usuario(self, uid, nombre, email, rol="alumno", nivel="secundaria", grupos=None, activo=True):
        datos = {"nombre": nombre, "email": (email or "").lower(), "rol": rol, "nivel": nivel,
                 "grupos": list(grupos or []), "activo": activo, "creado": config.iso(), "consentimiento": None}
        self.s.set("usuarios", uid, datos, merge=False)
        return {**datos, "uid": uid}

    def actualizar_usuario(self, uid, **campos):
        self.s.set("usuarios", uid, campos, merge=True)

    def listar_usuarios(self, rol=None, gid=None):
        if gid:
            res = self.s.query("usuarios", [("grupos", "array_contains", gid)])
            if rol:
                res = [r for r in res if r.get("rol") == rol]
        elif rol:
            res = self.s.query("usuarios", [("rol", "==", rol)])
        else:
            res = self.s.query("usuarios")
        for r in res:
            r["uid"] = r.pop("id")
        return sorted(res, key=lambda r: r.get("nombre", "").lower())

    def registrar_consentimiento(self, uid):
        self.actualizar_usuario(uid, consentimiento={"version": config.VERSION_AVISO, "fecha": config.iso()})

    def eliminar_datos_usuario(self, uid):
        """Derecho de supresión: borra todo lo asociado al usuario (no borra la cuenta de acceso)."""
        for col in ("eventos", "feedback", "alertas", "tarjetas", "encuestas"):
            for d in self.s.query(col, [("uid", "==", uid)]):
                self.s.delete(col, d["id"])
        for d in self.s.query("uso_diario", [("uid", "==", uid)]):
            self.s.delete("uso_diario", d["id"])
        self.s.delete("progreso", uid)
        self.s.delete("usuarios", uid)

    # ---------- grupos ----------
    def crear_grupo(self, nombre, nivel="secundaria", docentes=None, meta_semanal=100):
        gid = slug(nombre)
        self.s.set("grupos", gid, {"nombre": nombre, "nivel": nivel, "docentes": list(docentes or []),
                                   "meta_semanal": meta_semanal, "creado": config.iso(),
                                   "codigo": self._codigo_unico(), "acceso_codigo": True}, merge=False)
        return gid

    # ---- acceso con código de grupo ----
    def _codigo_unico(self):
        for _ in range(20):
            c = "".join(_secrets.choice(ALFABETO_CODIGO) for _ in range(6))
            if not self.s.query("grupos", [("codigo", "==", c)], limite=1):
                return c
        raise RuntimeError("No pude generar un código único.")

    def codigo_de_grupo(self, gid):
        g = self.s.get("grupos", gid) or {}
        if not g.get("codigo"):
            g["codigo"] = self._codigo_unico()
            self.s.set("grupos", gid, {"codigo": g["codigo"]})
        return g["codigo"]

    def regenerar_codigo(self, gid):
        c = self._codigo_unico()
        self.s.set("grupos", gid, {"codigo": c})
        return c

    def buscar_grupo_por_codigo(self, codigo):
        c = normalizar_codigo(codigo)
        if len(c) != 6:
            return None
        res = self.s.query("grupos", [("codigo", "==", c)], limite=1)
        if not res:
            return None
        g = res[0]
        g["gid"] = g.pop("id")
        return g if g.get("acceso_codigo", True) else None

    def entrar_con_codigo(self, nombre, codigo):
        """Alumno que entra con nombre y código del grupo. Devuelve (perfil|None, mensaje_de_error|None)."""
        nombre = " ".join(str(nombre or "").split())[:60]
        if len(nombre) < 3:
            return None, "Escribe tu nombre y apellido."
        g = self.buscar_grupo_por_codigo(codigo)
        if g is None:
            return None, "El código no es válido. Pídele a tu docente el código correcto."
        uid = "c_" + slug(f"{g['gid']}_{normalizar(nombre)}")
        perfil = self.get_usuario(uid)
        if perfil is None:
            perfil = self.crear_usuario(uid, nombre, "", "alumno", g.get("nivel", "secundaria"), [g["gid"]])
        elif not perfil.get("activo", True):
            return None, "Tu cuenta está desactivada. Habla con tu docente."
        return perfil, None

    def get_grupo(self, gid):
        d = self.s.get("grupos", gid)
        if d is not None:
            d["gid"] = gid
        return d

    def listar_grupos(self):
        res = self.s.query("grupos")
        for r in res:
            r["gid"] = r.pop("id")
        return sorted(res, key=lambda r: r.get("nombre", "").lower())

    def actualizar_grupo(self, gid, **campos):
        self.s.set("grupos", gid, campos, merge=True)

    def grupos_de_docente(self, uid):
        return [g for g in self.listar_grupos() if uid in g.get("docentes", [])]

    def asignar_grupo(self, uid, gid):
        u = self.get_usuario(uid) or {}
        gs = list(u.get("grupos", []))
        if gid not in gs:
            gs.append(gid)
        self.actualizar_usuario(uid, grupos=gs)

    # ---------- progreso ----------
    def get_progreso(self, uid):
        base = {k: (dict(v) if isinstance(v, dict) else v) for k, v in PROGRESO_BASE.items()}
        base.update(self.s.get("progreso", uid) or {})
        return base

    def registrar_actividad(self, uid, tipo, xp=0, tema=None):
        p = self.get_progreso(uid)
        hoy = config.hoy()
        antes = progress.nivel(p["xp"])[0]
        if tipo == "mensaje":
            cupo = p.get("xp_msg") or {}
            if cupo.get("dia") != hoy:
                cupo = {"dia": hoy, "n": 0}
            if cupo["n"] < progress.MAX_XP_MSG_DIA:
                cupo["n"] += 1
                xp = progress.XP_MENSAJE
            else:
                xp = 0
            p["xp_msg"] = cupo
            p["mensajes"] += 1
        elif tipo == "quiz":
            p["quizzes"] += 1
        elif tipo == "reto":
            p["retos"] += 1
        p["xp"] += xp
        p["racha"] = progress.actualizar_racha(p.get("ultimo_dia"), hoy, p.get("racha", 0))
        p["mejor_racha"] = max(p.get("mejor_racha", 0), p["racha"])
        p["ultimo_dia"] = hoy
        if tema:
            p["ultimo_tema"] = clave(tema, 60)
        self.s.set("progreso", uid, p, merge=True)
        despues = progress.nivel(p["xp"])
        return {"xp": xp, "total": p["xp"], "racha": p["racha"], "subio": despues[0] > antes, "nivel": despues[1]}

    def anotar_resultado(self, uid, tema, aciertos, total):
        p = self.get_progreso(uid)
        k = clave(tema)
        p["aciertos"] += aciertos
        p["preguntas"] += total
        destino = "dominados" if total and aciertos / total >= 0.8 else "dificultades"
        p[destino][k] = p[destino].get(k, 0) + 1
        self.s.set("progreso", uid, p, merge=True)

    def actualizar_memoria(self, uid, memoria, dominados=(), dificultades=()):
        p = self.get_progreso(uid)
        p["memoria"] = (memoria or "")[:600]
        for t in dominados:
            p["dominados"][clave(t)] = p["dominados"].get(clave(t), 0) + 1
        for t in dificultades:
            p["dificultades"][clave(t)] = p["dificultades"].get(clave(t), 0) + 1
        self.s.set("progreso", uid, p, merge=True)

    # ---------- eventos y uso ----------
    def registrar_evento(self, uid, gid, tipo, materia="", tema="", ok=True, tin=0, tout=0):
        self.s.add("eventos", {"uid": uid, "gid": gid or "", "dia": config.hoy(), "tipo": tipo, "materia": materia,
                               "tema": clave(tema, 60) if tema else "", "ok": bool(ok), "tin": tin, "tout": tout,
                               "ts": config.iso()})

    def eventos_grupo(self, gid, dias=7):
        res = []
        for d in config.dias_atras(dias):
            res += self.s.query("eventos", [("gid", "==", gid), ("dia", "==", d)])
        return res

    def uso_diario(self, uid, dia=None):
        dia = dia or config.hoy()
        return self.s.get("uso_diario", f"{uid}_{dia}") or {"msgs": 0, "gen": 0, "tin": 0, "tout": 0}

    def sumar_uso(self, uid, msgs=0, gen=0, tin=0, tout=0):
        dia = config.hoy()
        d = {"msgs": msgs, "gen": gen, "tin": tin, "tout": tout}
        self.s.set("uso_diario", f"{uid}_{dia}", {"uid": uid, "dia": dia}, merge=True)
        self.s.incr("uso_diario", f"{uid}_{dia}", d)
        self.s.set("uso_global", dia, {"dia": dia}, merge=True)
        self.s.incr("uso_global", dia, d)

    def uso_global(self, dia=None):
        dia = dia or config.hoy()
        return self.s.get("uso_global", dia) or {"msgs": 0, "gen": 0, "tin": 0, "tout": 0}

    # ---------- retroalimentación y alertas ----------
    def guardar_feedback(self, uid, gid, valor, materia="", pregunta="", respuesta="", guardar_texto=True):
        self.s.add("feedback", {"uid": uid, "gid": gid or "", "dia": config.hoy(), "valor": int(valor),
                                "materia": materia, "pregunta": pregunta[:400] if guardar_texto else "",
                                "respuesta": respuesta[:600] if guardar_texto else "", "ts": config.iso()})

    def listar_feedback(self, gid):
        return sorted(self.s.query("feedback", [("gid", "==", gid)]), key=lambda x: x.get("ts", ""), reverse=True)

    def crear_alerta(self, uid, nombre, gid, categorias, fragmento):
        self.s.add("alertas", {"uid": uid, "nombre": nombre, "gid": gid or "", "categorias": list(categorias),
                               "fragmento": fragmento[:200], "dia": config.hoy(), "ts": config.iso(),
                               "estado": "nueva", "atendida_por": None})

    def listar_alertas(self, estado=None):
        filtros = [("estado", "==", estado)] if estado else []
        return sorted(self.s.query("alertas", filtros), key=lambda x: x.get("ts", ""), reverse=True)

    def marcar_alerta(self, aid, por):
        self.s.set("alertas", aid, {"estado": "atendida", "atendida_por": por, "atendida_ts": config.iso()})

    # ---------- material de la escuela ----------
    def guardar_material(self, titulo, texto, gids, materia="General", autor=""):
        mid = self.s.add("materiales", {"titulo": titulo, "materia": materia, "gids": list(gids) or ["*"],
                                        "autor": autor, "ts": config.iso(), "activo": True, "n": 0})
        frags = trocear(texto)
        for i, f in enumerate(frags):
            self.s.add("fragmentos", {"mid": mid, "orden": i, "texto": f})
        self.s.set("materiales", mid, {"n": len(frags)})
        return mid, len(frags)

    def listar_materiales(self, gid=None):
        if gid:
            res = {m["id"]: m for m in self.s.query("materiales", [("gids", "array_contains", gid)])}
            res.update({m["id"]: m for m in self.s.query("materiales", [("gids", "array_contains", "*")])})
            lista = list(res.values())
        else:
            lista = self.s.query("materiales")
        return sorted(lista, key=lambda m: m.get("ts", ""), reverse=True)

    def desactivar_material(self, mid):
        self.s.set("materiales", mid, {"activo": False})

    def eliminar_material(self, mid):
        for f in self.s.query("fragmentos", [("mid", "==", mid)]):
            self.s.delete("fragmentos", f["id"])
        self.s.delete("materiales", mid)

    def fragmentos_de_grupo(self, gid):
        frags = []
        for m in self.listar_materiales(gid):
            if not m.get("activo", True):
                continue
            for f in self.s.query("fragmentos", [("mid", "==", m["id"])]):
                frags.append({"id": f["id"], "mid": m["id"], "titulo": m.get("titulo", ""), "orden": f.get("orden", 0),
                              "texto": f.get("texto", "")})
        return sorted(frags, key=lambda f: (f["mid"], f["orden"]))

    # ---------- tarjetas de repaso ----------
    def tarjetas_usuario(self, uid):
        res = self.s.query("tarjetas", [("uid", "==", uid)])
        for r in res:
            r["tid"] = r.pop("id")
        return res

    def agregar_tarjetas(self, uid, tarjetas):
        existentes = {t["pregunta"].strip().lower() for t in self.tarjetas_usuario(uid)}
        n = 0
        for t in tarjetas:
            if t["pregunta"].strip().lower() in existentes:
                continue
            self.s.add("tarjetas", {**t, "uid": uid})
            existentes.add(t["pregunta"].strip().lower())
            n += 1
        return n

    def guardar_tarjeta(self, tid, tarjeta):
        self.s.set("tarjetas", tid, {k: v for k, v in tarjeta.items() if k != "tid"})

    def tarjetas_pendientes(self, uid, limite=10):
        return spaced.pendientes(self.tarjetas_usuario(uid), config.hoy(), limite)

    # ---------- retos diarios y avisos ----------
    def get_reto(self, gid, materia):
        return self.s.get("retos", f"{slug(gid)}_{slug(materia)}_{config.hoy()}")

    def guardar_reto(self, gid, materia, preguntas):
        self.s.set("retos", f"{slug(gid)}_{slug(materia)}_{config.hoy()}",
                   {"gid": gid, "materia": materia, "dia": config.hoy(), "preguntas": preguntas}, merge=False)

    def reto_hecho(self, uid, materia):
        return any(e.get("materia") == materia for e in
                   self.s.query("eventos", [("uid", "==", uid), ("dia", "==", config.hoy()), ("tipo", "==", "reto")]))

    def publicar_aviso(self, gid, texto, autor, dias=7):
        self.s.add("avisos", {"gid": gid, "texto": texto[:400], "autor": autor, "ts": config.iso(),
                              "hasta": spaced_dias(dias)})

    def avisos_vigentes(self, gids):
        hoy, res = config.hoy(), []
        for g in gids:
            res += [a for a in self.s.query("avisos", [("gid", "==", g)]) if a.get("hasta", "") >= hoy]
        return sorted(res, key=lambda a: a.get("ts", ""), reverse=True)

    # ---------- correo, encuestas, errores y respaldo ----------
    def buscar_por_email(self, email):
        res = self.s.query("usuarios", [("email", "==", (email or "").lower())], limite=1)
        if not res:
            return None
        d = res[0]
        d["uid"] = d.pop("id")
        return d

    def guardar_encuesta(self, uid, rol, gid, puntaje, comentario=""):
        self.s.add("encuestas", {"uid": uid, "rol": rol, "gid": gid or "", "puntaje": int(puntaje),
                                 "comentario": (comentario or "")[:300], "dia": config.hoy(), "ts": config.iso()})

    def listar_encuestas(self):
        return sorted(self.s.query("encuestas"), key=lambda x: x.get("ts", ""), reverse=True)

    def registrar_error(self, donde, detalle=""):
        self.s.add("errores", {"donde": donde, "detalle": str(detalle)[:200], "dia": config.hoy(), "ts": config.iso()})

    def errores_recientes(self, dias=7):
        res = []
        for d in config.dias_atras(dias):
            res += self.s.query("errores", [("dia", "==", d)])
        return sorted(res, key=lambda x: x.get("ts", ""), reverse=True)

    def registrar_auditoria(self, accion, detalle=""):
        self.s.add("auditoria", {"accion": accion, "detalle": str(detalle)[:120], "dia": config.hoy(), "ts": config.iso()})

    def auditoria_dia(self, dia):
        return self.s.query("auditoria", [("dia", "==", dia)])

    def auditoria_reciente(self, dias=7):
        res = []
        for d in config.dias_atras(dias):
            res += self.auditoria_dia(d)
        return sorted(res, key=lambda x: x.get("ts", ""), reverse=True)

    def eventos_dia(self, dia):
        return self.s.query("eventos", [("dia", "==", dia)])

    def exportar(self):
        """Respaldo completo (información confidencial)."""
        return {c: self.s.query(c) for c in COLECCIONES}

    def importar(self, datos):
        """Restaura un respaldo hecho con exportar(). Devuelve {colección: registros restaurados}."""
        if not isinstance(datos, dict):
            raise ValueError("El archivo no es un respaldo válido.")
        cuenta = {}
        for col in COLECCIONES:
            docs = datos.get(col)
            if not isinstance(docs, list):
                continue
            n = 0
            for d in docs:
                if isinstance(d, dict) and "id" in d:
                    d = dict(d)
                    self.s.set(col, str(d.pop("id")), d, merge=False)
                    n += 1
            cuenta[col] = n
        if not cuenta:
            raise ValueError("El archivo no parece un respaldo del Tutor Modelista.")
        return cuenta

    # ---------- configuración de la escuela ----------
    def get_config(self):
        return {**CONFIG_DEFECTO, **(self.s.get("config", "escuela") or {})}

    def set_config(self, **campos):
        self.s.set("config", "escuela", campos, merge=True)


    # ---------- contraseñas de usuarios (acceso sin Firebase) ----------
    def fijar_clave_usuario(self, uid, clave):
        clave = (clave or "").strip()
        if len(clave) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres.")
        sal = _secrets.token_hex(16)
        self.s.set("usuarios", uid, {"clave_sal": sal, "clave_hash": self._hash(clave, sal)})

    def nueva_clave_temporal(self, uid):
        clave = "".join(_secrets.choice(ALFABETO_CODIGO) for _ in range(8))
        self.fijar_clave_usuario(uid, clave)
        return clave

    def entrar_con_clave(self, email, clave):
        """Docente/personal con correo y contraseña guardada aquí. Devuelve (perfil|None, error|None)."""
        email = (email or "").strip().lower()
        malo = (None, "Correo o contraseña incorrectos.")
        if not email or not clave:
            return malo
        perfil = self.buscar_por_email(email)
        if not perfil or not perfil.get("clave_hash"):
            return malo
        if not hmac.compare_digest(self._hash(clave.strip(), perfil["clave_sal"]), perfil["clave_hash"]):
            return malo
        if not perfil.get("activo", True):
            return None, "Tu cuenta está desactivada. Habla con la administración."
        return perfil, None

    # ---------- instalación (contraseña del administrador y clave de Gemini) ----------
    # Viven en su propia colección, que NO entra en el respaldo descargable (exportar), para no filtrar secretos.
    ITERACIONES = 200_000
    MIN_CLAVE_ADMIN = 8

    def instalacion(self):
        return self.s.get("instalacion", "unica") or {}

    def instalacion_lista(self):
        return bool(self.instalacion().get("admin_hash"))

    def nombre_escuela(self):
        return self.instalacion().get("escuela") or ""

    def _hash(self, clave, sal):
        return hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), bytes.fromhex(sal), self.ITERACIONES).hex()

    def fijar_clave_admin(self, clave):
        clave = (clave or "").strip()
        if len(clave) < self.MIN_CLAVE_ADMIN:
            raise ValueError(f"La contraseña debe tener al menos {self.MIN_CLAVE_ADMIN} caracteres.")
        sal = _secrets.token_hex(16)
        self.s.set("instalacion", "unica", {"admin_sal": sal, "admin_hash": self._hash(clave, sal)})

    def verificar_admin(self, clave):
        d = self.instalacion()
        if not d.get("admin_hash") or not clave:
            return False
        return hmac.compare_digest(self._hash(clave.strip(), d["admin_sal"]), d["admin_hash"])

    def configurar_instalacion(self, escuela, clave_admin, gemini_key="", primer_grupo="", nivel="secundaria"):
        """Primer arranque: guarda la contraseña del administrador (cifrada), el nombre de la escuela, la clave de
        Gemini (opcional) y crea el primer grupo si se pidió. Devuelve el código del grupo o ''."""
        if self.instalacion_lista():
            raise ValueError("La plataforma ya fue configurada.")
        self.fijar_clave_admin(clave_admin)
        self.s.set("instalacion", "unica", {"escuela": (escuela or "").strip()[:80], "creada": config.iso()})
        if (gemini_key or "").strip():
            self.guardar_clave_gemini(gemini_key)
        primer_grupo = (primer_grupo or "").strip()
        if primer_grupo:
            gid = self.crear_grupo(primer_grupo, nivel)
            return self.codigo_de_grupo(gid)
        return ""

    def guardar_clave_gemini(self, clave):
        clave = (clave or "").strip()
        self.s.set("instalacion", "unica", {"gemini_key": clave})
        config.fijar_clave_guardada(clave)

    def guardar_nombre_escuela(self, nombre):
        self.s.set("instalacion", "unica", {"escuela": (nombre or "").strip()[:80]})

    def clave_gemini_guardada(self):
        return self.instalacion().get("gemini_key") or ""


def spaced_dias(n):
    return spaced.sumar_dias(config.hoy(), n)
