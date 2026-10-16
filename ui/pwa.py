"""Preparación de la página: evita que el navegador la traduzca (rompe Streamlit) y, si está activo,
la hace instalable en el celular (mejor esfuerzo; requiere 'enableStaticServing = true' y la carpeta static/)."""
import streamlit as st
import streamlit.components.v1 as components

from tm import config

_BASE = """
  d.documentElement.setAttribute('lang', 'es');
  d.documentElement.setAttribute('translate', 'no');
  if (!d.querySelector('meta[name=google]')) {
    const g = d.createElement('meta'); g.name = 'google'; g.content = 'notranslate'; d.head.appendChild(g);
  }
"""
_PWA = """
  if (!d.querySelector('link[rel=manifest]')) {
    const l = d.createElement('link'); l.rel = 'manifest'; l.href = '/app/static/manifest.json'; d.head.appendChild(l);
    const i = d.createElement('link'); i.rel = 'apple-touch-icon'; i.href = '/app/static/icono-192.png'; d.head.appendChild(i);
    const m = d.createElement('meta'); m.name = 'theme-color'; m.content = '#061A66'; d.head.appendChild(m);
  }
"""


def inyectar():
    """Una vez por sesión: idioma español sin traducción automática y (opcional) manifiesto para instalar."""
    if st.session_state.get("_pwa"):
        return
    st.session_state["_pwa"] = True
    js = _BASE + (_PWA if config.leer_bool("PWA", True) else "")
    components.html("<script>try { const d = window.parent.document;" + js + "} catch (e) {}</script>", height=0)
