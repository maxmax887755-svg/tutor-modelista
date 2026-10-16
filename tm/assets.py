"""Asegura que las imágenes de Antorchita existan, aunque la carpeta assets no se haya subido al repositorio."""
import base64
import os
import shutil
import tempfile

from .assets_embebidos import EMBEBIDOS


def _escribir(carpeta, nombre, b64):
    with open(os.path.join(carpeta, nombre), "wb") as f:
        f.write(base64.b64decode("".join(b64)))


def asegurar_assets(carpeta, embebidos=None):
    """Devuelve una carpeta que contiene todas las imágenes. Si faltan, las crea en 'carpeta';
    si no se puede escribir ahí, usa una carpeta temporal (copiando antes lo que ya hubiera)."""
    embebidos = EMBEBIDOS if embebidos is None else embebidos
    if all(os.path.isfile(os.path.join(carpeta, n)) for n in embebidos):
        return carpeta
    try:
        os.makedirs(carpeta, exist_ok=True)
        for n in embebidos:
            if not os.path.isfile(os.path.join(carpeta, n)):
                _escribir(carpeta, n, embebidos[n])
        return carpeta
    except OSError:
        pass
    tmp = os.path.join(tempfile.gettempdir(), "tutor_modelista_assets")
    os.makedirs(tmp, exist_ok=True)
    if os.path.isdir(carpeta):
        for f in os.listdir(carpeta):
            origen = os.path.join(carpeta, f)
            if os.path.isfile(origen):
                shutil.copy(origen, os.path.join(tmp, f))
    for n in embebidos:
        if not os.path.isfile(os.path.join(tmp, n)):
            _escribir(tmp, n, embebidos[n])
    return tmp
