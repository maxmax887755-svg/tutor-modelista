# Tutor Modelista · Escuela Modelo, Mérida

Plataforma educativa con IA (Gemini) y la mascota Antorchita.
Modos: Estudiante Secundaria, Estudiante Preparatoria y Docente.

## Conseguir la API key de Gemini
1. Entra a https://aistudio.google.com/apikey e inicia sesión con una cuenta de Google.
2. Acepta los términos de servicio.
3. Pulsa **Create API key**, ponle un nombre (por ejemplo `tutor-modelista`) y elige el proyecto
   (si es tu primera vez, AI Studio crea uno por ti).
4. Copia la clave (empieza con `AIza...`) y guárdala solo en `.env` o en los *Secrets* de Streamlit.
   **Nunca** la subas a GitHub ni la pegues en el código.

## Ejecutar en local
1. Copia `.env.example` como `.env` y pega tu clave
   (o copia `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml`).
2. Crea el entorno, instala dependencias y ejecuta:
   ```
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   streamlit run app.py
   ```

## Desplegar en Streamlit Cloud
1. Sube el proyecto a GitHub (el `.gitignore` protege tus secretos).
2. En https://share.streamlit.io crea una app nueva apuntando a `app.py`.
3. En *Settings → Secrets* pega:
   ```
   GEMINI_API_KEY = "tu_clave"
   ACCESS_CODE = "un-codigo-para-la-demo"
   ```
4. Despliega. Comparte el link y el código solo con quienes vayan a probarla.

## Configuración opcional (secretos o `.env`)
| Variable | Para qué sirve | Por defecto |
|---|---|---|
| `ACCESS_CODE` | Pide un código antes de entrar | sin código |
| `MAX_MENSAJES` | Tope de mensajes por sesión | 40 |
| `GEMINI_MODEL_ESTUDIANTE` | Modelo para estudiantes (rápido, razonamiento mínimo) | `gemini-3.5-flash-lite` |
| `GEMINI_MODEL_DOCENTE` | Modelo para docentes (más capaz) | `gemini-3.8-flash` |
| `GEMINI_MODEL_RESPALDO` | Modelo si falla el principal | el modelo del otro rol |

Los modelos de Google cambian con frecuencia. Revisa los vigentes en
https://ai.google.dev/gemini-api/docs/models y cámbialos con las variables de arriba, sin tocar el código.

## Privacidad
Con alumnos menores de edad, antes de un uso real revisa los términos de datos de la API de Gemini
(https://ai.google.dev/gemini-api/terms). En general, los servicios gratuitos pueden tener condiciones
distintas a los de pago respecto al uso de los datos; para producción conviene usar facturación
habilitada y publicar un aviso de privacidad. La app no guarda conversaciones.

## Imágenes de la mascota (opcional)
Copia a `assets/` una imagen por situación (PNG con fondo transparente, o webp/gif/jpg) y la app las usa sola:

| Archivo | Cuándo aparece |
|---|---|
| `antorchita_saludo.png` | Pantalla de bienvenida |
| `antorchita_pensando.png` | Mientras prepara la respuesta |
| `antorchita_celebrando.png` | Cada vez que la IA responde y, con aviso, cuando la llama del alumno sube de nivel |
| `antorchita_adios.png` | (opcional) Al limpiar la conversación |

Recomendado: unos 600 px de alto y menos de 150 KB cada una. Las de más de 700 KB se ignoran.
Si faltan, la app usa la mascota animada de `mascota_cuerpo.webp` y `mascota_brazo.webp`, y si tampoco están, funciona igual sin mascota.
También acepta animaciones Lottie (`antorchita_saludo.json`, `antorchita_pensando.json`, `antorchita_celebrando.json`, `antorchita_adios.json`), que tienen prioridad sobre las imágenes.

## Multimedia
Ver `assets/README.md`. La app funciona aunque falten archivos.
