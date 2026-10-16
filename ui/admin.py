"""Administración: usuarios (alta, CSV, baja), grupos, uso y costos, límites y privacidad."""
import csv
import io
import json

import streamlit as st

import nucleo
from tm import auth, config, csvimport, estado, ia, quotas
from tm.repo import slug

from . import comun

ROLES = ["alumno", "docente", "orientador", "admin"]
NIVELES = ["secundaria", "preparatoria"]


def _asegurar_grupo(repo, nombre, nivel, docente_uid=None):
    if not nombre:
        return None
    gid = slug(nombre)
    if repo.get_grupo(gid) is None:
        repo.crear_grupo(nombre, nivel)
    if docente_uid:
        g = repo.get_grupo(gid)
        if docente_uid not in g.get("docentes", []):
            repo.actualizar_grupo(gid, docentes=g.get("docentes", []) + [docente_uid])
    return gid


def alta_usuario(ctx, fila):
    """Crea la cuenta y el perfil. Devuelve {'email', 'clave'|None, 'ok', 'detalle'}."""
    repo = ctx.repo
    email = fila["email"]
    usa_clave_local = False
    try:
        if ctx.modo == "firebase" and config.acceso_correo():
            uid, clave = auth.crear_cuenta(email, fila["nombre"])
        else:
            uid, clave = "u_" + slug(email), None
            usa_clave_local = True
        existente = repo.get_usuario(uid)
        gid = _asegurar_grupo(repo, fila.get("grupo"), fila["nivel"], uid if fila["rol"] == "docente" else None)
        grupos = [gid] if gid else []
        if existente:
            repo.actualizar_usuario(uid, nombre=fila["nombre"], rol=fila["rol"], nivel=fila["nivel"],
                                    grupos=sorted(set(existente.get("grupos", [])) | set(grupos)), activo=True)
        else:
            repo.crear_usuario(uid, fila["nombre"], email, fila["rol"], fila["nivel"], grupos)
        if usa_clave_local:
            clave = repo.nueva_clave_temporal(uid)       # sin Firebase: la contraseña se guarda aquí y se entrega en la lista
        if ctx.modo == "firebase" and config.acceso_correo() and clave and config.api_key_firebase():
            auth.enviar_restablecer(config.api_key_firebase(), email)
        return {"email": email, "clave": clave, "ok": True, "detalle": "creado" if clave or not config.acceso_correo() or ctx.modo != "firebase" else "ya existía"}
    except Exception:
        nucleo.logger.exception("No pude dar de alta a %s", email)
        return {"email": email, "clave": None, "ok": False, "detalle": "error al crear"}


def _csv_credenciales(resultados):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["email", "estado", "contraseña_temporal"])
    for r in resultados:
        w.writerow([r["email"], r["detalle"], r["clave"] or ""])
    return buf.getvalue()


def _tab_usuarios(ctx):
    usuarios = ctx.repo.listar_usuarios()
    st.caption(f"{len(usuarios)} usuario(s) en total.")
    if usuarios:
        st.dataframe([{"Nombre": u["nombre"], "Correo": u.get("email"), "Rol": u["rol"], "Nivel": u.get("nivel"),
                       "Grupos": ", ".join(u.get("grupos", [])), "Activo": u.get("activo", True)} for u in usuarios],
                     use_container_width=True)
    with st.expander("➕ Crear un usuario"):
        with st.form("alta_uno"):
            nombre = st.text_input("Nombre completo")
            email = st.text_input("Correo")
            c1, c2, c3 = st.columns(3)
            rol, nivel, grupo = c1.selectbox("Rol", ROLES), c2.selectbox("Nivel", NIVELES), c3.text_input("Grupo (ej. 1A Secundaria)")
            ok = st.form_submit_button("Crear", use_container_width=True)
        if ok:
            filas, errores = csvimport.parsear_csv(f"nombre,email,rol,nivel,grupo\n\"{nombre}\",{email},{rol},{nivel},\"{grupo}\"")
            if errores:
                st.warning(errores[0])
            else:
                r = alta_usuario(ctx, filas[0])
                st.session_state.credenciales = [r]
                if not r["ok"]:
                    st.error("No pude crearlo.")
                elif r["clave"] and not config.acceso_correo():
                    st.success(f"{r['email']} creado. Contraseña temporal (anótala, no se vuelve a mostrar): **{r['clave']}**")
                else:
                    st.success(f"{r['email']}: {r['detalle']}." + (" Se envió un correo para crear contraseña." if r["clave"] else ""))
    with st.expander("📥 Importar desde CSV"):
        st.caption("Columnas: nombre,email,rol,nivel,grupo (rol y nivel opcionales). Máximo 500 filas.")
        archivo = st.file_uploader("Archivo CSV", type=["csv"], key="csv_usuarios")
        if archivo is not None:
            filas, errores = csvimport.parsear_csv(archivo.getvalue().decode("utf-8-sig", errors="replace"))
            for e in errores[:10]:
                st.warning(e)
            st.write(f"{len(filas)} fila(s) válidas.")
            if filas and st.button("Crear estos usuarios", key="crear_csv"):
                with st.spinner("Creando cuentas…"):
                    st.session_state.credenciales = [alta_usuario(ctx, f) for f in filas]
                st.success("Listo.")
    creds = st.session_state.get("credenciales")
    if creds:
        st.download_button("⬇️ Descargar lista (contraseñas temporales, se muestran una sola vez)", _csv_credenciales(creds),
                           file_name="usuarios_nuevos.csv", key="dl_creds")
    if usuarios:
        st.subheader("Gestionar un usuario")
        mapa = {f"{u['nombre']} ({u.get('email')})": u for u in usuarios}
        u = mapa[st.selectbox("Usuario", list(mapa), key="usuario_gest")]
        c1, c2 = st.columns(2)
        activo = u.get("activo", True)
        if c1.button("Desactivar" if activo else "Activar", use_container_width=True, key="toggle_activo"):
            ctx.repo.actualizar_usuario(u["uid"], activo=not activo)
            if ctx.modo == "firebase":
                try:
                    auth.desactivar_cuenta(u["uid"], activo)
                except Exception:
                    nucleo.logger.exception("No pude cambiar el estado de la cuenta")
            st.rerun()
        if not (ctx.modo == "firebase" and config.acceso_correo()) and u.get("email") and c2.button("Generar contraseña nueva", use_container_width=True, key="clave_nueva_usuario"):
            st.success(f"Contraseña nueva para {u['nombre']} (anótala, no se vuelve a mostrar): **{ctx.repo.nueva_clave_temporal(u['uid'])}**")
        if ctx.modo == "firebase" and u.get("email") and c2.button("Enviar correo de contraseña", use_container_width=True, key="reset_usuario"):
            auth.enviar_restablecer(config.api_key_firebase(), u["email"])
            st.success("Correo enviado.")


def _tab_grupos(ctx):
    grupos = ctx.repo.listar_grupos()
    docentes = ctx.repo.listar_usuarios(rol="docente")
    mapa_g = {g["nombre"]: g for g in grupos}
    st.dataframe([{"Grupo": g["nombre"], "Nivel": g.get("nivel"), "Código de acceso": ctx.repo.codigo_de_grupo(g["gid"]),
                   "Docentes": len(g.get("docentes", [])), "Meta semanal": g.get("meta_semanal")} for g in grupos],
                 use_container_width=True)
    with st.form("nuevo_grupo"):
        nombre = st.text_input("Nombre del grupo (ej. 2B Preparatoria)")
        nivel = st.selectbox("Nivel", NIVELES)
        if st.form_submit_button("Crear grupo", use_container_width=True) and nombre.strip():
            _asegurar_grupo(ctx.repo, nombre.strip(), nivel)
            st.rerun()
    if grupos and docentes:
        st.subheader("Asignar docentes")
        g = mapa_g[st.selectbox("Grupo", list(mapa_g), key="grupo_asig")]
        mapa_d = {f"{d['nombre']} ({d.get('email')})": d["uid"] for d in docentes}
        previos = [k for k, v in mapa_d.items() if v in g.get("docentes", [])]
        elegidos = st.multiselect("Docentes del grupo", list(mapa_d), default=previos, key="docentes_grupo")
        if st.button("Guardar docentes", key="guardar_docentes"):
            ctx.repo.actualizar_grupo(g["gid"], docentes=[mapa_d[k] for k in elegidos])
            for k in elegidos:
                ctx.repo.asignar_grupo(mapa_d[k], g["gid"])
            st.success("Docentes asignados.")
    alumnos = ctx.repo.listar_usuarios(rol="alumno")
    if grupos and alumnos:
        st.subheader("Asignar alumnos")
        g2 = mapa_g[st.selectbox("Grupo", list(mapa_g), key="grupo_asig_al")]
        mapa_a = {f"{a['nombre']} ({a.get('email')})": a["uid"] for a in alumnos}
        sel = st.multiselect("Alumnos a agregar a este grupo", list(mapa_a), key="alumnos_grupo")
        if st.button("Agregar alumnos", key="agregar_alumnos"):
            for k in sel:
                ctx.repo.asignar_grupo(mapa_a[k], g2["gid"])
            st.success("Alumnos agregados.")


def _tab_uso(ctx):
    cfg = ctx.repo.get_config()
    p_in, p_out = config.leer_float("COSTO_ENTRADA_POR_MILLON", 0.0), config.leer_float("COSTO_SALIDA_POR_MILLON", 0.0)
    filas = []
    for d in config.dias_atras(7):
        u = ctx.repo.uso_global(d)
        filas.append({"Día": d, "Mensajes": u.get("msgs", 0), "Generaciones": u.get("gen", 0),
                      "Tokens entrada": u.get("tin", 0), "Tokens salida": u.get("tout", 0),
                      "Costo estimado USD": quotas.costo_estimado(u.get("tin", 0), u.get("tout", 0), p_in, p_out)})
    hoy = filas[0]
    st.metric("Mensajes hoy", f"{hoy['Mensajes']} / {cfg['tope_global_mensajes']}")
    if hoy["Mensajes"] >= cfg["tope_global_mensajes"] * 0.8:
        st.warning("Estás cerca del tope diario de mensajes de la escuela. Revisa los límites o la cuota de la API.")
    st.dataframe(filas, use_container_width=True)
    if not (p_in or p_out):
        st.caption("Para ver costos en dinero, define COSTO_ENTRADA_POR_MILLON y COSTO_SALIDA_POR_MILLON en los secretos "
                   "(precios por millón de tokens, según la página de precios de Google).")


def _tab_config(ctx):
    cfg = ctx.repo.get_config()
    with st.form("form_cfg"):
        valores = {}
        for rol in ROLES:
            valores[f"limite_{rol}"] = st.number_input(f"Mensajes por día ({rol})", 1, 1000,
                                                       int(cfg.get(f"limite_{rol}", quotas.LIMITES_DEFECTO[rol])), key=f"cfg_{rol}")
        valores["tope_global_mensajes"] = st.number_input("Tope global de mensajes por día", 100, 100000, int(cfg["tope_global_mensajes"]), key="cfg_tope")
        if st.form_submit_button("Guardar límites", use_container_width=True):
            ctx.repo.set_config(**{k: int(v) for k, v in valores.items()})
            st.session_state.pop("_cache", None)
            st.success("Guardado.")


def _tab_privacidad(ctx):
    st.markdown("**Derecho de supresión.** Borra los datos de un usuario (progreso, tarjetas, retroalimentación, alertas, "
                "uso y perfil). La cuenta de acceso en Firebase no se elimina aquí.")
    usuarios = ctx.repo.listar_usuarios()
    if not usuarios:
        return
    mapa = {f"{u['nombre']} ({u.get('email')})": u["uid"] for u in usuarios}
    elegido = st.selectbox("Usuario", list(mapa), key="usuario_borrar")
    seguro = st.checkbox("Entiendo que esto no se puede deshacer", key="seguro_borrar")
    if st.button("Borrar sus datos", disabled=not seguro, key="borrar_datos"):
        ctx.repo.eliminar_datos_usuario(mapa[elegido])
        st.success("Datos borrados.")


def _tab_estado(ctx):
    st.caption("Revisa que todo esté en ✅ antes de abrir la plataforma a los alumnos.")
    items = estado.diagnostico(ctx.modo, tiene_clave=ctx.repo.instalacion_lista())
    st.info("👉 **Siguiente paso:** " + estado.siguiente_paso(items))
    for item in items:
        st.markdown(f"{'✅' if item['ok'] else '⚠️'} **{item['nombre']}** — {item['detalle']}")
    if st.button("Probar la IA ahora", key="probar_ia"):
        try:
            with st.spinner("Probando…"):
                texto, _ = ia.generar("Responde solo con la palabra: listo", max_tokens=20)
            st.success(f"La IA respondió: {texto[:40]}")
        except ia.IAError:
            st.error("La IA no respondió. Revisa la clave de Gemini, el modelo y la cuota.")


def _tab_respaldo(ctx):
    st.warning("El respaldo contiene información confidencial de la escuela. Guárdalo en un lugar seguro.")
    if st.button("Preparar respaldo completo", key="preparar_respaldo"):
        st.session_state.respaldo = json.dumps(ctx.repo.exportar(), ensure_ascii=False, default=str)
    if st.session_state.get("respaldo"):
        st.download_button("⬇️ Descargar respaldo (JSON)", st.session_state.respaldo, file_name="respaldo_tutor_modelista.json", key="dl_respaldo")
    st.subheader("Restaurar un respaldo")
    st.caption("Útil si la base de datos se reinició. Sobrescribe los registros que tengan el mismo identificador.")
    archivo = st.file_uploader("Archivo de respaldo (JSON)", type=["json"], key="restaurar_json")
    if archivo is not None and st.button("Restaurar ahora", key="restaurar"):
        try:
            cuenta = ctx.repo.importar(json.loads(archivo.getvalue().decode("utf-8")))
        except (ValueError, UnicodeDecodeError):
            st.error("El archivo no es un respaldo válido.")
        else:
            st.session_state.pop("_cache", None)
            st.success(f"Restaurado: {sum(cuenta.values())} registros.")
    st.subheader("Accesos de administración (7 días)")
    accesos = ctx.repo.auditoria_reciente(7)
    if accesos:
        nombres = {"admin_codigo_ok": "Entró con el código", "admin_codigo_fallo": "Intento fallido con el código"}
        st.dataframe([{"Cuándo": a.get("ts"), "Qué": nombres.get(a.get("accion"), a.get("accion"))} for a in accesos[:50]], use_container_width=True)
    else:
        st.caption("Sin accesos con código registrados.")
    st.subheader("Errores recientes (7 días)")
    errores = ctx.repo.errores_recientes(7)
    if errores:
        st.dataframe([{"Día": e.get("dia"), "Dónde": e.get("donde"), "Detalle": e.get("detalle")} for e in errores[:50]], use_container_width=True)
    else:
        st.success("Sin errores registrados.")


def _tab_instalacion(ctx):
    """Nombre de la escuela, clave de Gemini y contraseña del administrador, editables sin tocar archivos."""
    repo = ctx.repo
    st.subheader("Datos de la escuela")
    with st.form("cfg_escuela"):
        nombre = st.text_input("Nombre de la escuela", value=repo.nombre_escuela())
        if st.form_submit_button("Guardar nombre"):
            repo.guardar_nombre_escuela(nombre)
            st.success("Guardado.")
    st.subheader("Clave de Gemini (la IA)")
    if config.leer("GEMINI_API_KEY"):
        st.caption("Ya hay una clave definida en los secretos del servidor; esa tiene prioridad.")
    elif repo.clave_gemini_guardada():
        st.caption("Hay una clave guardada. Pega otra abajo para reemplazarla.")
    else:
        st.warning("Aún no hay clave de Gemini: el tutor no podrá responder. Consíguela gratis en https://aistudio.google.com/apikey")
    with st.form("cfg_gemini"):
        clave = st.text_input("Nueva clave de Gemini", type="password")
        if st.form_submit_button("Guardar clave"):
            if len(clave.strip()) < 20:
                st.error("La clave parece incompleta.")
            else:
                repo.guardar_clave_gemini(clave)
                st.success("Clave guardada. Ya puedes probar el tutor.")
    st.subheader("Contraseña de administrador")
    with st.form("cfg_clave_admin"):
        actual = st.text_input("Contraseña actual", type="password")
        nueva = st.text_input("Contraseña nueva (mínimo 8 caracteres)", type="password")
        if st.form_submit_button("Cambiar contraseña"):
            if not repo.verificar_admin(actual):
                st.error("La contraseña actual no coincide.")
            else:
                try:
                    repo.fijar_clave_admin(nueva)
                    repo.registrar_auditoria("admin_clave_cambiada")
                    st.success("Contraseña cambiada.")
                except ValueError as e:
                    st.error(str(e))


def pagina_admin(ctx):
    nucleo.aplicar_tema(nucleo.ES_DOCENTE)
    st.header("🛠️ Administración")
    if ctx.modo == "temporal":
        st.warning("Este servidor borra su disco al reiniciarse: los usuarios y el progreso se perderían. "
                   "Para uso real instala la plataforma en un equipo de la escuela o conecta Firebase.")
    pestañas = st.tabs(["👥 Usuarios", "🏫 Grupos", "💰 Uso y costos", "⚙️ Límites", "🔧 Configuración", "🩺 Estado", "💾 Respaldo y errores", "🔒 Privacidad"])
    for tab, fn in zip(pestañas, (_tab_usuarios, _tab_grupos, _tab_uso, _tab_config, _tab_instalacion, _tab_estado, _tab_respaldo, _tab_privacidad)):
        with tab:
            fn(ctx)
