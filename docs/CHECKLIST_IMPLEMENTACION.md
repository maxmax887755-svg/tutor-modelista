# Checklist para entregar la plataforma a una escuela

## Lo que resuelve la plataforma
Cuentas (Google o correo), roles, progreso, quizzes, repaso, retos, material de la escuela, panel docente, panel de dirección con reporte, encuesta, alertas de bienestar, límites y control de gasto, estado del sistema, respaldo, registro de errores y accesibilidad.

## Acceso de los alumnos
- **Código de grupo** (listo desde el primer día): nombre + código; no verifica identidad, ideal para un piloto.
- **Google o correo y contraseña**: cada alumno con su cuenta; recomendado para uso amplio.

## Lo que debe resolver la escuela (no es código)
- [ ] **Aviso de privacidad** revisado por la dirección y asesoría legal; autorizaciones de las familias.
- [ ] **Protocolo de bienestar:** quién atiende las alertas y cómo.
- [ ] **Facturación de Gemini** activada y un tope de gasto en Google Cloud.
- [ ] **Hosting estable** si pasa de piloto (Streamlit Cloud gratuito se duerme y tiene límites).
- [ ] **Responsable técnico** que pueda revisar 🩺 Estado y los errores.
- [ ] **Respaldo periódico** (🛠️ Administración → 💾 Respaldo) guardado en un lugar seguro; se puede restaurar desde la misma pantalla.

## Puesta en marcha (en este orden)
0. **Ruta recomendada:** `docs/INSTALACION_EN_LA_ESCUELA.md` (equipo de la escuela, datos permanentes, sin Firebase). Alternativa en la nube: `docs/DESPLIEGUE_STREAMLIT_CLOUD.md`: publicar con `CODIGO_ADMIN` y confirmar que `MODO_DEMO` no esté activo.
1. `docs/FIREBASE_PASO_A_PASO.md` y, si quieren cuentas de Google, `docs/CONFIGURAR_GOOGLE.md`.
2. Entrar como administrador y revisar **🩺 Estado**: todo en ✅.
3. Crear grupos, docentes y alumnos (CSV).
4. Subir materiales de cada grupo.
5. `docs/PRUEBAS_ANTES_DE_USAR.md` y `python evaluar_calidad.py`.
6. Capacitar a docentes con `docs/GUIA_DOCENTE.md` y compartir `docs/GUIA_ALUMNOS.md` con familias.
7. Arrancar el piloto (`docs/PROPUESTA_PILOTO.md`).
