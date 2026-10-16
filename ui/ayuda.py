"""Ayuda por rol y guía de primera vez."""
import streamlit as st

import nucleo

from . import comun

TOUR_ALUMNO = ("👋 **Primera vez aquí.** 1) Elige la materia y pregúntale a Antorchita lo que no entiendas: te guía con preguntas. "
               "2) Haz un **Quiz** o el **Reto del día** para sumar puntos y hacer crecer tu llama. "
               "3) En **Repaso** volverás a practicar lo que te costó. Más ayuda en ❓ **Ayuda**.")
TOUR_PERSONAL = ("👋 **Primera vez aquí.** Planea clases y analiza documentos en el **Asistente**. En **Materiales** sube lecturas para que "
                 "el tutor explique con lo que ven en clase, y en **Mi grupo** revisa el avance. Más ayuda en ❓ **Ayuda**.")

AYUDA = {
    "alumno": """### Para estudiantes
**¿Antorchita me da las respuestas?** No: te guía con preguntas y pistas para que tú descubras el camino. Así aprendes de verdad.

**¿Cómo gano puntos?** Chateando con el tutor (hasta 20 puntos al día), con quizzes, con el reto del día y repasando tarjetas.

**¿Qué es la racha?** Los días seguidos que estudias. Si faltas un día, no la pierdes.

**¿Qué hace Repaso?** Te vuelve a preguntar lo que fallaste, justo cuando conviene recordarlo.

**¿Puedo mandar una foto?** Sí: abre *Foto del ejercicio*. Antorchita te guía sin resolverlo.

**¿Mis conversaciones se guardan?** No. Se guarda tu progreso, no tus mensajes. No escribas datos personales.

**Si algo te preocupa o te hacen daño,** habla hoy con un adulto de confianza o con tu orientador.""",
    "docente": """### Para docentes
**Asistente:** planeación, rúbricas, secuencias didácticas, adaptaciones por nivel. Puedes subir un documento (PDF, DOCX o TXT) y preguntar sobre él.

**Materiales:** sube lecturas y temarios por grupo. El tutor los usa para explicar y cita la fuente (por ejemplo [F2]).

**Mi grupo:** resumen de uso, temas que más se dificultan, respuestas por mejorar (👎), avisos, meta semanal, reporte para familias y reto del día.

**Privacidad:** solo ves datos de uso y progreso, no las conversaciones de los alumnos.

**Consejo:** pide a tus alumnos 10 minutos con el tutor una vez por semana y comenta en clase los temas que aparecen como difíciles.""",
    "orientador": """### Para orientación
**Bienestar:** aquí llegan alertas cuando un mensaje sugiere riesgo (autolesión, violencia, acoso, abuso). Es una ayuda automática y puede fallar: sigue siempre el protocolo de la escuela. La información es confidencial.""",
    "admin": """### Para administración
**Dirección:** adopción, uso por día, grupos, satisfacción y un reporte descargable para la directora.

**Administración:** usuarios (uno por uno o por CSV), grupos, uso y costos, límites diarios, estado del sistema, respaldo y privacidad.

**Antes de abrir a alumnos:** revisa 🩺 *Estado* (todo en ✅), el aviso de privacidad y `docs/PRUEBAS_ANTES_DE_USAR.md`.""",
}


def tour(ctx):
    if ctx.usuario.get("tour"):
        return
    st.info(TOUR_ALUMNO if ctx.es_alumno else TOUR_PERSONAL)
    if st.button("¡Entendido, vamos!", key="tour_ok"):
        ctx.repo.actualizar_usuario(ctx.uid, tour=True)
        ctx.usuario["tour"] = True
        st.rerun()


def pagina_ayuda(ctx):
    nucleo.aplicar_tema(ctx.rol_nucleo)
    comun.chip_rol(ctx)
    st.header("❓ Ayuda")
    st.markdown(AYUDA.get(ctx.rol, AYUDA["alumno"]))
    st.divider()
    st.caption("Las respuestas de la IA pueden tener errores: verifícalas con tu docente. "
               "Creada por Maximiliano Ávila Castillo para la Escuela Modelo.")
