import requests

URL = "http://localhost:8000/chat"

print("RockBot - Guía de Escalada (escribe 'salir' para terminar)\n")

while True:
    mensaje = input("Tú: ").strip()
    if mensaje.lower() in ("salir", "exit", "quit"):
        print("¡Hasta la próxima escalador!")
        break
    if not mensaje:
        continue

    try:
        res = requests.post(URL, json={"message": mensaje})
        respuesta = res.json().get("response", "Sin respuesta")
        print(f"\nRockBot: {respuesta}\n")
    except Exception as e:
        print(f"Error: {e}\n")