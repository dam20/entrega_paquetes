import pytesseract
from PIL import ImageGrab
import pyautogui
import json
import time
import keyboard
import requests
import os
import sys

CONFIG_FILE = "config.json"
SERVER_URL = "http://localhost:8000/pedido"  # Cambiar IP si el servidor está en otra PC

def calibrar():
    print("Colocá el mouse sobre la esquina superior izquierda del campo NRO. PIEZA y presioná Enter")
    input()
    pieza_top_left = pyautogui.position()

    print("Ahora colocá el mouse sobre la esquina inferior derecha del campo NRO. PIEZA y presioná Enter")
    input()
    pieza_bottom_right = pyautogui.position()

    print("Ahora colocá el mouse sobre la esquina superior izquierda del campo LUGAR DE GUARDA y presioná Enter")
    input()
    guarda_top_left = pyautogui.position()

    print("Ahora colocá el mouse sobre la esquina inferior derecha del campo LUGAR DE GUARDA y presioná Enter")
    input()
    guarda_bottom_right = pyautogui.position()

    config = {
        "pieza": {
            "top_left": pieza_top_left,
            "bottom_right": pieza_bottom_right
        },
        "guarda": {
            "top_left": guarda_top_left,
            "bottom_right": guarda_bottom_right
        }
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    print("Calibración guardada en config.json")

def capturar_texto(area):
    x1 = area["top_left"]["x"]
    y1 = area["top_left"]["y"]
    x2 = area["bottom_right"]["x"]
    y2 = area["bottom_right"]["y"]
    bbox = (x1, y1, x2, y2)
    imagen = ImageGrab.grab(bbox)
    texto = pytesseract.image_to_string(imagen, config="--psm 6").strip()
    return texto

def main_loop():
    if not os.path.exists(CONFIG_FILE):
        print("Primero debes calibrar la aplicación con: python app.py --calibrate")
        sys.exit(1)

    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    print("Escuchando tecla F9...")

    while True:
        if keyboard.is_pressed('F9'):
            print("Capturando...")
            pieza = capturar_texto(config["pieza"])
            guarda = capturar_texto(config["guarda"])

            pieza = pieza.replace(" ", "").upper()
            guarda = ''.join(filter(str.isdigit, guarda))

            print(f"Pieza: {pieza}, Guarda: {guarda}")

            if len(pieza) >= 12 and guarda.isdigit():
                payload = {
                    "pieza": pieza,
                    "guarda": guarda
                }
                try:
                    r = requests.post(SERVER_URL, json=payload)
                    print("Enviado:", r.status_code)
                except Exception as e:
                    print("Error al enviar:", e)
            else:
                print("Datos inválidos. Revisar OCR.")
            
            time.sleep(1.5)  # para evitar múltiples lecturas por pulsación

# Entrada principal
if __name__ == "__main__":
    if "--calibrate" in sys.argv:
        calibrar()
    else:
        main_loop()
