"""Panel de dirección: visión general del piloto y reporte descargable."""
import streamlit as st

import nucleo
from tm import ia, prompts2, reports

from . import comun


def pagina_direccion(ctx):
    nucleo.aplicar_tema(nucleo.ES_DOCENTE)
    st.header("📈 Dirección")
    st.caption("Visión general del uso de la plataforma. Solo datos de uso y progreso; no se muestran conversaciones.")
    if st.button("🔄 Actualizar datos", key="act_dir"):
        st.session_state.get("_cache", {}).pop("escuela", None)
    d = comun.cacheado("escuela", lambda: reports.resumen_escuela(ctx.repo, 14), 120)

    a, b, c, e = st.columns(4)
    a.metric("Alumnos registrados", d["alumnos"])
    b.metric("Activos (7 días)", f"{d['activos7']} ({d['adopcion']}%)")
    c.metric("Quizzes y retos", d["quizzes"] + d["retos"])
    e.metric("Mensajes al tutor", d["mensajes"])

    st.subheader("Actividad de los últimos 14 días")
    st.line_chart({"Actividad": [d["serie"][x]["eventos"] for x in d["dias"]],
                   "Alumnos activos": [d["serie"][x]["activos"] for x in d["dias"]]})

    f1, f2, f3 = st.columns(3)
    f1.metric("Respuestas útiles", f"{d['satisfaccion']}%" if d["satisfaccion"] is not None else "—")
    f2.metric("Encuesta (de 5)", d["encuesta_prom"] if d["encuesta_prom"] is not None else "—")
    f3.metric("Errores (7 días)", d["errores"])

    st.subheader("Por grupo (últimos 7 días)")
    if d["grupos"]:
        st.dataframe([{"Grupo": g["nombre"], "Alumnos": g["alumnos"], "Activos": g["activos"], "Mensajes": g["mensajes"],
                       "Quizzes y retos": g["quizzes_retos"]} for g in d["grupos"]], use_container_width=True)
    else:
        st.caption("Aún no hay grupos.")
    if d["dificultades"]:
        st.subheader("Temas que más se dificultan")
        st.bar_chart({t: n for t, n in d["dificultades"]})
    if d["comentarios"]:
        st.subheader("Comentarios recientes (anónimos)")
        for com in d["comentarios"]:
            st.markdown(f"- ({com['rol']}, {com['puntaje']}/5) {com['comentario']}")

    st.divider()
    st.subheader("Reporte para la dirección")
    if st.button("✨ Redactar resumen y recomendaciones con IA", key="resumen_ia_dir"):
        try:
            with st.spinner("Redactando…"):
                texto, _ = ia.generar(prompts2.prompt_resumen_direccion(reports.reporte_direccion_md(d)),
                                      max_tokens=700, rol=nucleo.ES_DOCENTE)
            st.session_state.resumen_dir = texto
        except ia.IAError:
            st.warning("No pude redactar el resumen ahora. Puedes descargar el reporte sin él.")
    md = reports.reporte_direccion_md(d, "Escuela Modelo", st.session_state.get("resumen_dir", ""))
    st.download_button("⬇️ Descargar reporte (.md)", md, file_name="reporte_piloto.md", key="dl_reporte_dir")
    with st.expander("Ver reporte"):
        st.markdown(md)
