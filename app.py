"""Tutor Modelista v2 · Escuela Modelo de Mérida, Yucatán
Accesos con Firebase, progreso por alumno, material de la escuela, quizzes, repaso, reto diario y panel docente."""
import streamlit as st

st.set_page_config(page_title="Tutor Modelista", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

import nucleo
from tm import config
from ui import accesibilidad, admin, ayuda, comun, direccion, docente, login, orientador, progreso, pwa, quizzes, repaso, reto, tutor


def _principal():
    comun.iniciar_estado()
    pwa.inyectar()
    repo, modo = comun.obtener_repo()
    usuario = st.session_state.usuario
    if usuario is None:
        login.pantalla(repo, modo)
        st.stop()
    ctx = comun.Ctx(repo, modo, usuario)
    if (usuario.get("consentimiento") or {}).get("version") != config.VERSION_AVISO:
        comun.pantalla_consentimiento(ctx)
        st.stop()
    accesibilidad.aplicar()
    paginas = {
        "💬 Tutor": tutor.pagina_tutor, "💬 Asistente": tutor.pagina_tutor,
        "🧠 Quiz": quizzes.pagina_quiz, "🔁 Repaso": repaso.pagina_repaso, "⭐ Reto del día": reto.pagina_reto,
        "🔥 Mi progreso": progreso.pagina_progreso, "👩‍🏫 Mi grupo": docente.pagina_grupo,
        "📚 Materiales": docente.pagina_materiales, "🫶 Bienestar": orientador.pagina_bienestar,
        "🛠️ Administración": admin.pagina_admin, "📈 Dirección": direccion.pagina_direccion, "❓ Ayuda": ayuda.pagina_ayuda,
    }
    pagina = comun.barra_lateral(ctx)
    try:
        paginas[pagina](ctx)
    except Exception as e:
        nucleo.logger.exception("Error en la pantalla %s", pagina)
        try:
            repo.registrar_error(pagina, f"{type(e).__name__}: {e}")
        except Exception:
            pass
        st.error("Algo salió mal en esta pantalla. Recarga la página; si sigue igual, avisa a tu docente o a la administración.")


def main():
    try:
        _principal()
    except Exception:
        nucleo.logger.exception("Error al abrir la plataforma")
        st.error("Algo salió mal al abrir la plataforma. Recarga la página en un minuto; "
                 "si sigue igual, avisa a la administración de la escuela.")


if __name__ == "__main__":
    main()
