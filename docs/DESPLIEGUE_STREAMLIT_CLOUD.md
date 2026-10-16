# Publicar en Streamlit Cloud (versión de producción)

## 1. Subir el proyecto a GitHub (con `app.py` en la raíz)
En la terminal, **dentro de la carpeta que contiene `app.py`**:
```
git init
git rev-parse --show-toplevel
```
La segunda línea debe mostrar una ruta que **termine en el nombre de esta carpeta**. Si muestra tu carpeta de usuario (`C:/Users/...` a secas), detente: ahí hay archivos personales. Entonces ejecuta `git init` otra vez dentro de la carpeta del proyecto o pídeme ayuda.
```
git add .
git status
```
Revisa que **no** aparezcan `.env`, `secrets.toml` ni `datos_locales.json`. Si todo bien:
```
git commit -m "Tutor Modelista 1.0"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/NOMBRE_DEL_REPO.git
git push -u origin main
```
(Crea antes el repositorio vacío y **privado** en https://github.com/new.)

## 2. Crear la app
En https://share.streamlit.io → **Create app**:
- **Repository:** tu repositorio · **Branch:** `main` · **Main file path:** `app.py`
- **Python version:** 3.11
- **Advanced settings → Secrets** (comillas rectas `"`, una línea por dato):
```
GEMINI_API_KEY = "tu_clave"
CODIGO_ADMIN = "una-frase-larga-y-secreta-solo-tuya"
```

## 3. Primer acceso
1. Abre el link y despliega **🔑 Acceso de administración**; escribe tu `CODIGO_ADMIN`.
2. Ve a **🛠️ Administración → 🩺 Estado** y revisa cada línea.
3. Para cuentas reales y datos permanentes, conecta Firebase (`FIREBASE_PASO_A_PASO.md`) y, si quieren, Google (`CONFIGURAR_GOOGLE.md`). Sin Firebase la base de datos es **temporal** (ruta corta: `PILOTO_EN_STREAMLIT_CLOUD.md`): los usuarios y el progreso se pierden cuando la app se reinicia.

## Cómo entran los alumnos
Sin configurar nada más, **con su nombre y el código de su grupo**: en 🛠️ Administración → 🏫 Grupos creas el grupo y ves su código (los docentes también lo ven en Mi grupo → 🔑 Código del grupo). Ese acceso no verifica identidad; para identificar a cada alumno usa Google o correo (`CONFIGURAR_GOOGLE.md`, `FIREBASE_PASO_A_PASO.md`).

## Seguridad del código de administrador
- Quien tenga el código controla todo: no lo compartas. Cámbialo en los secretos si sospechas que se filtró (Manage app → Settings → Secrets → Reboot).
- Mejor 16 caracteres o más. Cada intento fallido espera un segundo, se limitan a 5 por sesión y 50 por día, y todo queda en **🛠️ Administración → 💾 Respaldo y errores**.

## Problemas comunes
- **"Invalid format: please enter valid TOML":** comillas curvas, valor sin comillas, línea repetida o texto ajeno pegado.
- **"This file does not exist":** el archivo no está en la raíz del repositorio. Revisa la ruta en GitHub.
- **Las imágenes:** la app trae las imágenes de Antorchita dentro del código y las crea sola si faltan.
