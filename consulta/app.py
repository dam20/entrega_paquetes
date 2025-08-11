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
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Tuple
import logging

# Configuración de logging
logging.basicConfig(
    filename='envios.log',
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

@dataclass
class CampoTexto:
    """Clase para representar un campo de texto extraído de la imagen"""
    y: int
    x: int
    texto: str

@dataclass
class DatosPaquete:
    """Clase para representar los datos del paquete"""
    pieza: str
    guarda: str

    def es_valido(self) -> bool:
        """Verifica si los datos del paquete son válidos"""
        return len(self.pieza) >= 12 and self.guarda.isdigit()

    def limpiar(self) -> 'DatosPaquete':
        """Limpia y formatea los datos del paquete"""
        pieza_limpia = re.sub(r'\W+$', '', self.pieza.replace(" ", "").upper())
        guarda_limpia = ''.join(filter(str.isdigit, self.guarda))
        return DatosPaquete(pieza_limpia, guarda_limpia)

class ImageProcessor(ABC):
    """Interfaz abstracta para el procesamiento de imágenes"""
    @abstractmethod
    def process(self, image: np.ndarray) -> Optional[np.ndarray]:
        pass

class WindowDetector(ImageProcessor):
    """Detector de ventanas con borde gris"""
    def __init__(self):
        self.lower = np.array([150, 150, 150], dtype=np.uint8)
        self.upper = np.array([170, 170, 170], dtype=np.uint8)
        self.kernel = np.ones((3, 3), np.uint8)

    def process(self, image: np.ndarray) -> Optional[np.ndarray]:
        mask = cv2.inRange(image, self.lower, self.upper)
        mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel)
        contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
            area = cv2.contourArea(cnt)
            if len(approx) == 4 and area > 1000:
                x, y, w, h = cv2.boundingRect(approx)
                return image[y+2:y+h-2, x+2:x+w-2]
        return None

class FieldExtractor(ImageProcessor):
    """Extractor de campos de texto de la imagen"""
    def __init__(self):
        self.target_white = self._hex_to_bgr('#FFFFFF')
        self.tolerance = 5
        self.lower_white = np.array([max(0, c-self.tolerance) for c in self.target_white])
        self.upper_white = np.array([min(255, c+self.tolerance) for c in self.target_white])

    def _hex_to_bgr(self, hex_color: str) -> Tuple[int, int, int]:
        """Convierte un color hexadecimal a BGR"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (4, 2, 0))

    def process(self, image: np.ndarray) -> List[CampoTexto]:
        mask_white = cv2.inRange(image, self.lower_white, self.upper_white)
        contornos, _ = cv2.findContours(mask_white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        resultados = []

        for c in contornos:
            x, y, w, h = cv2.boundingRect(c)
            if w > 30 and h > 10:
                campo = image[y:y+h, x:x+w]
                texto = pytesseract.image_to_string(campo, config='--psm 7').strip()
                if texto:
                    resultados.append(CampoTexto(y, x, texto))

        return sorted(resultados, key=lambda x: (x.y, x.x))

class ServerCommunicator:
    """Clase para manejar la comunicación con el servidor"""
    def __init__(self, server_url: str):
        self.server_url = server_url

    def enviar_datos(self, datos: DatosPaquete) -> bool:
        """Envía los datos al servidor y retorna si fue exitoso"""
        try:
            payload = {"pieza": datos.pieza, "guarda": datos.guarda}
            response = requests.post(self.server_url, json=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            logging.error(f"Error al enviar datos: {e}")
            return False

class ConsultaApp:
    """Clase principal de la aplicación"""
    def __init__(self, server_url: str):
        self.window_detector = WindowDetector()
        self.field_extractor = FieldExtractor()
        self.server = ServerCommunicator(server_url)
        self.running = True

    def capturar_pantalla(self) -> np.ndarray:
        """Captura la pantalla completa"""
        imagen = ImageGrab.grab()
        img_np = np.array(imagen)
        return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    def procesar_campos(self, campos: List[CampoTexto]) -> Optional[DatosPaquete]:
        """Procesa los campos extraídos y retorna los datos del paquete"""
        if len(campos) >= 13:
            return DatosPaquete(
                pieza=campos[0].texto,
                guarda=campos[11].texto
            ).limpiar()
        return None

    def manejar_captura(self):
        """Maneja el proceso de captura y procesamiento de imagen"""
        logging.info("Iniciando captura de pantalla")
        img = self.capturar_pantalla()
        ventana = self.window_detector.process(img)

        if ventana is None:
            logging.warning("No se detectó la ventana con borde gris")
            return

        campos = self.field_extractor.process(ventana)
        datos = self.procesar_campos(campos)

        if datos is None:
            logging.warning("No se detectaron suficientes campos")
            return

        if not datos.es_valido():
            logging.warning(f"Datos inválidos: {datos}")
            return

        if self.server.enviar_datos(datos):
            logging.info(f"✅ Datos enviados correctamente: {datos}")
        else:
            logging.error(f"❌ Error al enviar datos: {datos}")

    def run(self):
        """Ejecuta el bucle principal de la aplicación"""
        print(f"▶ Esperando tecla F4 para capturar pantalla. (ESC para salir)")
        print(f"🌐 Servidor destino: {self.server.server_url}")

        while self.running:
            if keyboard.is_pressed('esc'):
                print("👋 Saliendo...")
                self.running = False
                break

            if keyboard.is_pressed('f4'):
                print("📸 Capturando pantalla...")
                self.manejar_captura()
                time.sleep(1.5)  # anti-rebote

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--server',
        type=str,
        default="http://localhost:8000/pedido",
        help='URL del servidor donde enviar los datos'
    )
    args = parser.parse_args()

    app = ConsultaApp(args.server)
    app.run()

if __name__ == "__main__":
    main()

