"""Convierte el archivo JSON de la cuenta de servicio de Firebase en el bloque [firebase_cuenta]
listo para pegar en los secretos de Streamlit (evita errores de formato TOML).
Uso:  python convertir_firebase.py C:\ruta\al\archivo.json"""
import json
import secrets
import sys

CAMPOS = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id", "token_uri"]


def main():
    if len(sys.argv) < 2:
        print("Uso: python convertir_firebase.py ruta\\al\\archivo.json")
        return 1
    with open(sys.argv[1], encoding="utf-8") as f:
        datos = json.load(f)
    faltan = [c for c in CAMPOS if c not in datos]
    if faltan:
        print("Este archivo no parece una cuenta de servicio. Le faltan:", ", ".join(faltan))
        return 1
    bloque = "\n".join(["[firebase_cuenta]"] + [f"{c} = {json.dumps(datos[c], ensure_ascii=False)}" for c in CAMPOS])
    with open("secrets_firebase.txt", "w", encoding="utf-8") as f:
        f.write(bloque + "\n")
    print(bloque)
    print("\n--- Listo ---")
    print("1) Pega el bloque de arriba AL FINAL de tus secretos en Streamlit.")
    print("2) BORRA secrets_firebase.txt y el archivo JSON original: son llaves maestras.")
    print("3) Para el acceso con Google, tu cookie_secret puede ser:", secrets.token_urlsafe(32))
    return 0


if __name__ == "__main__":
    sys.exit(main())
