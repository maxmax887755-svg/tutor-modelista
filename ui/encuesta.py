"""Encuesta corta de opinión (sirve de evidencia durante el piloto)."""
import streamlit as st


def encuesta_lateral(ctx):
    with st.expander("💬 Cuéntanos qué tal vas"):
        with st.form("form_encuesta", clear_on_submit=True):
            puntaje = st.radio("¿Qué tan útil te ha sido?", [5, 4, 3, 2, 1], horizontal=True, key="enc_p",
                               format_func=lambda n: "⭐" * n)
            comentario = st.text_area("¿Qué mejorarías? (opcional)", max_chars=300, key="enc_c")
            enviar = st.form_submit_button("Enviar", use_container_width=True)
        if enviar:
            ctx.repo.guardar_encuesta(ctx.uid, ctx.rol, ctx.gid, puntaje, comentario)
            st.success("¡Gracias por tu opinión! 💙")
        st.caption("No escribas datos personales.")
