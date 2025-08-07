import cv2
import numpy as np
import pytesseract
import requests
import time
from PIL import ImageGrab
import keyboard
import argparse
import re
import sys
from datetime import datetime


# ---------- FUNCIONES ----------

def hex_to_bgr(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (4, 2, 0))  # BGR

def detectar_ventana(img):
    lower = np.array([150, 150, 150], dtype=np.uint8)
    upper = np.array([170, 170, 170], dtype=np.uint8)
    mask = cv2.inRange(img, lower, upper)
    kernel = np.ones((3, 3), np.uint8)
    mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
        area = cv2.contourArea(cnt)
        if len(approx) == 4 and area > 1000:
            x, y, w, h = cv2.boundingRect(approx)
            return img[y+2:y+h-2, x+2:x+w-2]
    return None

def extraer_campos(ventana_img):
    target_white = hex_to_bgr('#FFFFFF')
    tolerance = 5
    lower_white = np.array([max(0, target_white[0]-tolerance),
                            max(0, target_white[1]-tolerance),
                            max(0, target_white[2]-tolerance)])
    upper_white = np.array([min(255, target_white[0]+tolerance),
                            min(255, target_white[1]+tolerance),
                            min(255, target_white[2]+tolerance)])

    mask_white = cv2.inRange(ventana_img, lower_white, upper_white)

    contornos, _ = cv2.findContours(mask_white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    resultados = []

    for c in contornos:
        x, y, w, h = cv2.boundingRect(c)
        if w > 30 and h > 10:
            campo = ventana_img[y:y+h, x:x+w]
            texto = pytesseract.image_to_string(campo, config='--psm 7').strip()
            if texto:
                resultados.append((y, x, texto))

    resultados.sort()
    return resultados

def enviar_datos(pieza, guarda, server_url):
    pieza = pieza.replace(" ", "").upper()
    pieza = re.sub(r'\W+$', '', pieza)
    guarda = ''.join(filter(str.isdigit, guarda))

    print(f"Pieza: {pieza}, Guarda: {guarda}")

    fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{fecha_hora}] Pieza: {pieza}, Guarda: {guarda} -> "

    if len(pieza) >= 12 and guarda.isdigit():
        payload = {"pieza": pieza, "guarda": guarda}
        try:
            r = requests.post(server_url, json=payload)
            estado = f"✅ Enviado: {r.status_code}"
            print(estado)
            log_entry += estado
        except Exception as e:
            estado = f"❌ Error al enviar: {e}"
            print(estado)
            log_entry += estado
    else:
        estado = "❌ Datos inválidos. Revisar OCR."
        print(estado)
        log_entry += estado

    # Guardar en archivo de log
    with open("envios_log.txt", "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

def capturar_pantalla_completa():
    imagen = ImageGrab.grab()
    img_np = np.array(imagen)
    return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

# ---------- MAIN ----------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', type=str, default="http://localhost:8000/pedido",
                        help='URL del servidor donde enviar los datos')
    args = parser.parse_args()

    server_url = args.server

    print(f"▶ Esperando tecla F4 para capturar pantalla. (ESC para salir)")
    print(f"🌐 Servidor destino: {server_url}")

    while True:
        if keyboard.is_pressed('esc'):
            print("👋 Saliendo...")
            break

        if keyboard.is_pressed('f4'):
            print("📸 Capturando pantalla...")

            img = capturar_pantalla_completa()
            ventana = detectar_ventana(img)

            if ventana is None:
                print("❌ No se detectó la ventana con borde gris.")
            else:
                campos = extraer_campos(ventana)

                if len(campos) >= 13:
                    pieza = campos[0][2]
                    guarda = campos[12][2]
                    enviar_datos(pieza, guarda, server_url)
                else:
                    print("❌ No se detectaron suficientes campos.")

            time.sleep(1.5)  # anti-rebote

if __name__ == "__main__":
    main()

