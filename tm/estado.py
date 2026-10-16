"""Revisión rápida de cómo está configurada la app (para la persona que la administra)."""
import os

import nucleo

from . import config


def diagnostico(modo, tiene_clave=False):
    """Lista de {nombre, ok, detalle}. 'ok' False significa algo por revisar."""
    cargar = nucleo.cargar_api_key()
    google, correo = config.acceso_google(), (modo == "firebase" and config.acceso_correo())
    grupo = config.acceso_grupo(google or correo)
    base = {"firebase": "Firebase conectado: los datos son permanentes.",
            "local": "Los datos se guardan de forma permanente en este equipo (con respaldo automático diario).",
            "temporal": "Este servidor borra su disco al reiniciar: los datos se perderían. Usa un equipo propio o Firebase.",
            "firebase_error": "Hay credenciales de Firebase pero no se pudo conectar."}.get(modo, modo)
    esperadas = ["antorchita.png", "antorchita_saludo.png", "antorchita_pensando.png", "antorchita_celebrando.png", "antorchita_adios.png"]
    faltan = [f for f in esperadas if not nucleo.existe(os.path.join(nucleo.ASSETS, f))]
    return [
        {"nombre": "Imágenes de Antorchita", "ok": not faltan,
         "detalle": "Todas encontradas." if not faltan else f"Faltan: {', '.join(faltan)} (carpeta buscada: {nucleo.ASSETS})."},
        {"nombre": "Clave de Gemini", "ok": bool(cargar), "detalle": "Configurada." if cargar else "Falta GEMINI_API_KEY."},
        {"nombre": "SDK de Gemini", "ok": nucleo.genai is not None, "detalle": "Instalado." if nucleo.genai else "Falta instalar google-genai."},
        {"nombre": "Base de datos", "ok": modo in ("firebase", "local"), "detalle": base},
        {"nombre": "Acceso con Google", "ok": google, "detalle": "Activo." if google else "No configurado (opcional)."},
        {"nombre": "Acceso con correo y contraseña", "ok": correo, "detalle": "Activo." if correo else "No configurado (opcional)."},
        {"nombre": "Modo demo apagado", "ok": not config.modo_demo(),
         "detalle": "Apagado: nadie puede elegir un rol de prueba." if not config.modo_demo()
         else ("Encendido, pero hay cuentas reales y el demo no se ofrece." if (google or correo)
               else "ENCENDIDO: cualquiera con el link elige un rol. No la uses con alumnos así (quita MODO_DEMO).")},
        {"nombre": "Acceso con código de grupo", "ok": grupo,
         "detalle": "Activo: los alumnos entran con su nombre y el código de su grupo (simple, pero no verifica identidad)." if grupo
         else "Desactivado."},
        {"nombre": "Alguien puede iniciar sesión", "ok": bool(google or correo or grupo or config.modo_demo() or config.codigo_admin()),
         "detalle": "Sí." if (google or correo or grupo or config.modo_demo() or config.codigo_admin()) else "Nadie: activa el acceso por código de grupo, Google o Firebase."},
        {"nombre": "Código de administrador", "ok": bool(config.codigo_admin()) or tiene_clave,
         "detalle": "Contraseña de administrador guardada (no la compartas)." if tiene_clave
         else ("Configurado en secretos (guárdalo bien y no lo compartas)." if config.codigo_admin()
               else "No hay contraseña de administrador. Cierra sesión y completa el asistente inicial.")},
        {"nombre": "Administradores definidos", "ok": bool(config.admin_emails()) or tiene_clave or bool(config.codigo_admin()),
         "detalle": f"{len(config.admin_emails())} correo(s) en ADMIN_EMAILS." if config.admin_emails()
         else ("Administra con la contraseña guardada." if (tiene_clave or config.codigo_admin()) else "Falta ADMIN_EMAILS.")},
        {"nombre": "Modelos de IA", "ok": True, "detalle": f"Estudiantes: {nucleo.MODELO_ESTUDIANTE} · Docentes: {nucleo.MODELO_DOCENTE}"},
        {"nombre": "Alertas de bienestar", "ok": config.leer_bool("ALERTAS_BIENESTAR", True),
         "detalle": "Activas." if config.leer_bool("ALERTAS_BIENESTAR", True) else "Desactivadas."},
    ]


def siguiente_paso(items):
    """La acción más importante pendiente, en una frase."""
    ok = {i["nombre"]: i["ok"] for i in items}
    if not ok.get("Clave de Gemini"):
        return "Pega tu clave de Gemini en Administración → 🔧 Configuración (o como GEMINI_API_KEY en los secretos)."
    if not ok.get("Base de datos"):
        return "Los datos no son permanentes en este servidor: instala la plataforma en un equipo de la escuela o conecta Firebase (docs/FIREBASE_PASO_A_PASO.md)."
    if not ok.get("Modo demo apagado"):
        return "Quita MODO_DEMO de los secretos."
    if not ok.get("Administradores definidos"):
        return "Agrega ADMIN_EMAILS en los secretos."
    if not (ok.get("Acceso con Google") or ok.get("Acceso con correo y contraseña")):
        if ok.get("Acceso con código de grupo"):
            return ("Listo para un piloto: crea grupos, comparte sus códigos y haz las pruebas de docs/PRUEBAS_ANTES_DE_USAR.md. "
                    "Para identificar a cada alumno con su cuenta, configura Google o correo (opcional).")
        return "Configura el acceso de alumnos y docentes: código de grupo, Google (docs/CONFIGURAR_GOOGLE.md) o correo y contraseña."
    return "Todo listo: crea grupos y usuarios, y haz las pruebas de docs/PRUEBAS_ANTES_DE_USAR.md."
