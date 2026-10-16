# Iniciar sesión con la cuenta de Google de la escuela

Ventajas: los alumnos y docentes no manejan contraseñas nuevas y **la sesión no se pierde al recargar la página**.

## 1. Requisitos
- Streamlit 1.42 o más nuevo (en tu computadora: `pip install -U streamlit`; Streamlit Cloud ya instala el nuevo con el `requirements.txt`).
- Una base de datos permanente (Firebase, ver `FIREBASE_PASO_A_PASO.md`): los perfiles se guardan ahí.

## 2. Crear las credenciales en Google
1. Entra a https://console.cloud.google.com con la cuenta de la escuela y elige o crea un proyecto.
2. **APIs y servicios → Pantalla de consentimiento de OAuth.** Si la escuela usa Google Workspace elige **Interno** (solo entran cuentas de la escuela); si no, **Externo**. Llena el nombre de la app y tu correo.
3. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth → Aplicación web.**
4. En **URI de redireccionamiento autorizados** agrega:
   - `https://TU-APP.streamlit.app/oauth2callback` (la dirección real de tu app en Streamlit Cloud)
   - `http://localhost:8501/oauth2callback` (para probar en tu computadora)
5. Copia el **ID de cliente** y el **Secreto de cliente**.

## 3. Ponerlo en los secretos
Agrega al final de los secretos (ver `.streamlit/secrets.toml.example`):
```
[auth]
redirect_uri = "https://TU-APP.streamlit.app/oauth2callback"
cookie_secret = "una-cadena-larga-y-aleatoria"
client_id = "xxxx.apps.googleusercontent.com"
client_secret = "xxxx"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```
Opcional: `DOMINIO_PERMITIDO = "tuescuela.edu.mx"` para aceptar solo ese dominio, y `ACCESO = "google"` para desactivar el acceso con contraseña.

## 4. Dar de alta a las personas
Entrar con Google **no basta**: la persona debe estar dada de alta con ese mismo correo en 🛠️ Administración → Usuarios (uno por uno o con CSV). Los correos de `ADMIN_EMAILS` entran como administrador aunque no estén dados de alta.

## Si algo falla
- "redirect_uri_mismatch": la URI de redireccionamiento no coincide exactamente con la de Google Cloud.
- "Tu correo aún no está dado de alta": falta crearlo en Administración.
- No aparece el botón de Google: falta la tabla `[auth]` o la versión de Streamlit es vieja.
