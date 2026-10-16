"""Pantalla de acceso: Google (cuenta de la escuela), correo y contraseña (Firebase) o modo demo con código opcional."""
import hmac
import time

import streamlit as st

import nucleo
from tm import auth, config

from tm.repo import slug

from . import comun

MAX_INTENTOS = 5
MAX_FALLOS_DIA = 50      # intentos fallidos del código de administrador por día (todas las sesiones)
PAUSA_FALLO = 1.0        # segundos de espera tras un intento fallido
UID_ADMIN_CODIGO = "admin_codigo"
DEMOS = {
    "Alumno de Secundaria": ("demo_alumno_sec", "alumno", "secundaria"),
    "Alumno de Preparatoria": ("demo_alumno_prepa", "alumno", "preparatoria"),
    "Docente": ("demo_docente", "docente", "secundaria"),
    "Orientador": ("demo_orientador", "orientador", "secundaria"),
    "Administrador": ("demo_admin", "admin", "secundaria"),
}


def _entrar(usuario):
    st.session_state.usuario = usuario
    st.rerun()


def perfil_google(repo):
    """Perfil de quien inició sesión con Google. Devuelve (perfil|None, mensaje_de_error|None)."""
    email = (getattr(st.user, "email", "") or "").strip().lower()
    if not email:
        return None, "Google no entregó tu correo. Intenta de nuevo."
    dominio = config.dominio_permitido()
    if dominio and not email.endswith("@" + dominio):
        return None, f"Usa tu cuenta de la escuela (@{dominio})."
    perfil = repo.buscar_por_email(email)
    es_admin = email in config.admin_emails()
    if perfil is None and es_admin:
        nombre = getattr(st.user, "name", None) or email.split("@")[0]
        perfil = repo.crear_usuario("g_" + slug(email), nombre, email, rol="admin")
    elif perfil is not None and es_admin and perfil.get("rol") != "admin":
        repo.actualizar_usuario(perfil["uid"], rol="admin")
        perfil["rol"] = "admin"
    if perfil is None:
        return None, "Tu correo aún no está dado de alta. Avisa a la administración de la escuela."
    if not perfil.get("activo", True):
        return None, "Tu cuenta está desactivada. Habla con la administración."
    return perfil, None


def _bloque_google(repo):
    if getattr(st.user, "is_logged_in", False):
        perfil, error = perfil_google(repo)
        if perfil:
            _entrar(perfil)
            return
        st.error(error)
        if st.button("Cerrar sesión de Google", key="logout_google", use_container_width=True):
            comun.cerrar_sesion()
        return
    if st.button("Entrar con Google", use_container_width=True, key="login_google"):
        st.login()


def _login_firebase(repo):
    if st.session_state.intentos_login >= MAX_INTENTOS:
        st.error("Demasiados intentos. Recarga la página e inténtalo de nuevo.")
        return
    with st.form("acceso"):
        email = st.text_input("Correo de la escuela")
        clave = st.text_input("Contraseña", type="password")
        enviar = st.form_submit_button("Entrar", use_container_width=True)
    if enviar:
        try:
            cuenta = auth.login(config.api_key_firebase(), email, clave)
        except auth.AuthError as e:
            st.session_state.intentos_login += 1
            st.error(str(e))
            return
        perfil = repo.get_usuario(cuenta["uid"])
        es_admin = cuenta["email"] in config.admin_emails()
        if perfil is None and es_admin:
            perfil = repo.crear_usuario(cuenta["uid"], cuenta["email"].split("@")[0], cuenta["email"], rol="admin")
        elif perfil is not None and es_admin and perfil.get("rol") != "admin":
            repo.actualizar_usuario(cuenta["uid"], rol="admin")
            perfil["rol"] = "admin"
        if perfil is None or not perfil.get("activo", True):
            st.error("Tu cuenta aún no está activada. Avisa a la administración de la escuela.")
            return
        _entrar(perfil)
    with st.expander("¿Olvidaste tu contraseña o es tu primera vez?"):
        correo = st.text_input("Tu correo", key="correo_reset")
        if st.button("Enviarme un correo para crear/cambiar contraseña", key="btn_reset"):
            auth.enviar_restablecer(config.api_key_firebase(), correo)
            st.success("Si el correo está registrado, recibirás un mensaje en unos minutos.")


def _login_demo(repo):
    codigo = config.leer("ACCESS_CODE")
    with st.form("acceso_demo"):
        if codigo:
            entrada = st.text_input("Código de acceso", type="password")
        quien = st.selectbox("Entrar como", list(DEMOS))
        enviar = st.form_submit_button("Entrar", use_container_width=True)
    if not enviar:
        return
    if st.session_state.intentos_login >= MAX_INTENTOS:
        st.error("Demasiados intentos. Recarga la página.")
        return
    if codigo and not hmac.compare_digest(entrada.encode("utf-8"), codigo.encode("utf-8")):
        st.session_state.intentos_login += 1
        st.error("Código incorrecto.")
        return
    uid, rol, nivel = DEMOS[quien]
    if repo.get_grupo("demo") is None:
        repo.crear_grupo("Demo", "secundaria", docentes=["demo_docente"])
    perfil = repo.get_usuario(uid)
    if perfil is None:
        perfil = repo.crear_usuario(uid, quien, f"{uid}@demo.local", rol, nivel, grupos=["demo"])
    _entrar(perfil)


def _login_codigo(repo):
    st.markdown("#### Entra con el código de tu grupo")
    with st.form("acceso_grupo"):
        nombre = st.text_input("Tu nombre y apellido")
        codigo = st.text_input("Código de tu grupo (te lo da tu docente)", max_chars=12)
        enviar = st.form_submit_button("Entrar a mi grupo", use_container_width=True)
    if not enviar:
        return
    if st.session_state.intentos_grupo >= MAX_INTENTOS:
        st.error("Demasiados intentos. Recarga la página.")
        return
    perfil, error = repo.entrar_con_codigo(nombre, codigo)
    if perfil:
        _entrar(perfil)
        return
    time.sleep(PAUSA_FALLO)
    st.session_state.intentos_grupo += 1
    st.error(error)


def _login_local(repo):
    """Docentes y personal cuando no hay Firebase: correo y la contraseña que les dio la administración."""
    with st.expander("👩‍🏫 Soy docente o personal de la escuela"):
        if st.session_state.intentos_login >= MAX_INTENTOS:
            st.error("Demasiados intentos. Recarga la página.")
            return
        with st.form("acceso_local"):
            email = st.text_input("Tu correo")
            clave = st.text_input("Tu contraseña", type="password")
            enviar = st.form_submit_button("Entrar", use_container_width=True)
        if not enviar:
            return
        perfil, error = repo.entrar_con_clave(email, clave)
        if perfil:
            _entrar(perfil)
            return
        time.sleep(PAUSA_FALLO)
        st.session_state.intentos_login += 1
        st.error(error)


def _perfil_admin_codigo(repo):
    from tm import config as cfg
    perfil = repo.get_usuario(UID_ADMIN_CODIGO)
    if perfil is None:
        repo.crear_usuario(UID_ADMIN_CODIGO, "Administración", "", rol="admin")
    # sin pantalla de aviso ni guía de primera vez para la cuenta de administración
    repo.actualizar_usuario(UID_ADMIN_CODIGO, rol="admin", activo=True, tour=True,
                            consentimiento={"version": cfg.VERSION_AVISO, "fecha": cfg.iso()})
    return repo.get_usuario(UID_ADMIN_CODIGO)


def _clave_admin_valida(repo, entrada):
    """True si coincide con la contraseña guardada en el asistente o con CODIGO_ADMIN de los secretos."""
    entrada = entrada or ""
    codigo = config.codigo_admin()
    if codigo and hmac.compare_digest(entrada.encode("utf-8"), codigo.encode("utf-8")):
        return True
    return repo.verificar_admin(entrada)


def _asistente_inicial(repo, modo):
    """Primer arranque: crea la contraseña del administrador, guarda la clave de Gemini y el primer grupo."""
    st.markdown("### 👋 ¡Bienvenido! Vamos a dejar todo listo")
    st.caption("Esto se hace una sola vez, en 2 minutos. Quien lo complete será el administrador de la plataforma.")
    if modo == "temporal":
        st.warning("Este servidor borra su disco al reiniciarse: los datos NO se conservarán. "
                   "Para uso real instala la plataforma en un equipo de la escuela o conecta Firebase (ver docs).")
    with st.form("asistente_inicial"):
        escuela = st.text_input("Nombre de la escuela", placeholder="Escuela Modelo")
        clave = st.text_input("Contraseña de administrador (mínimo 8 caracteres)", type="password")
        clave2 = st.text_input("Repite la contraseña", type="password")
        gemini = st.text_input("Clave de Gemini (opcional, la puedes poner después)", type="password",
                               help="Se obtiene gratis en https://aistudio.google.com/apikey")
        c1, c2 = st.columns([2, 1])
        grupo = c1.text_input("Primer grupo (opcional)", placeholder="1A Secundaria")
        nivel = c2.selectbox("Nivel", ["secundaria", "preparatoria"])
        enviar = st.form_submit_button("Guardar y entrar", use_container_width=True)
    if not enviar:
        return
    if not escuela.strip():
        st.error("Escribe el nombre de la escuela.")
    elif clave != clave2:
        st.error("Las contraseñas no coinciden.")
    else:
        try:
            repo.configurar_instalacion(escuela, clave, gemini, grupo, nivel)
        except ValueError as e:
            st.error(str(e))
            return
        repo.registrar_auditoria("instalacion_inicial")
        _entrar(_perfil_admin_codigo(repo))


def _acceso_admin(repo, abierto=False):
    """Acceso del administrador con la contraseña del asistente inicial o con CODIGO_ADMIN (secretos)."""
    with st.expander("🔑 Acceso de administración", expanded=abierto):
        with st.form("acceso_admin"):
            entrada = st.text_input("Contraseña o código de administrador", type="password")
            enviar = st.form_submit_button("Entrar como administrador", use_container_width=True)
        if not enviar:
            return
        if st.session_state.intentos_admin >= MAX_INTENTOS:
            st.error("Demasiados intentos. Recarga la página.")
            return
        fallos = sum(1 for a in repo.auditoria_dia(config.hoy()) if a.get("accion") == "admin_codigo_fallo")
        if fallos >= MAX_FALLOS_DIA:
            st.error("Acceso con código bloqueado por hoy por exceso de intentos. Usa tu cuenta de la escuela.")
            return
        if _clave_admin_valida(repo, entrada):
            repo.registrar_auditoria("admin_codigo_ok")
            _entrar(_perfil_admin_codigo(repo))
            return
        time.sleep(PAUSA_FALLO)
        st.session_state.intentos_admin += 1
        repo.registrar_auditoria("admin_codigo_fallo")
        st.error("Código incorrecto.")


def pantalla(repo, modo):
    nucleo.aplicar_tema(nucleo.ROLES[0])
    _, c, _ = st.columns([1, 2, 1])
    with c:
        if nucleo.existe(nucleo.LOGO):
            st.image(nucleo.LOGO, width=140)
        st.title("Tutor Modelista")
        st.caption(f"{repo.nombre_escuela() or 'Escuela Modelo'} · Asistente educativo con IA")
        google, correo = config.acceso_google(), (modo == "firebase" and config.acceso_correo())
        demo = config.modo_demo() and not google and not correo
        grupo = config.acceso_grupo(google or correo)
        hay_admin = bool(repo.instalacion_lista() or config.codigo_admin() or config.admin_emails())
        if modo == "firebase_error":
            st.error("No pude conectar con la base de datos de la escuela. Avisa a la persona responsable.")
        elif not hay_admin and not demo and not (google or correo) and not repo.listar_grupos():
            _asistente_inicial(repo, modo)       # primer arranque: no hay nada que "configurar" a mano
        else:
            if google:
                _bloque_google(repo)
            if google and correo:
                st.caption("— o con tu correo y contraseña —")
            if correo:
                _login_firebase(repo)
            if demo:
                _login_demo(repo)
            if grupo:
                _login_codigo(repo)
            if not (google or correo):
                _login_local(repo)
            sin_metodos = not (google or correo or demo or grupo)
            if sin_metodos:
                st.info("Los alumnos y docentes entran con el acceso que su escuela les indique. "
                        "Si eres administrador, entra aquí abajo.")
            if config.codigo_admin() or repo.instalacion_lista():
                _acceso_admin(repo, abierto=sin_metodos)
        comun.boton_creador("creador_login")
