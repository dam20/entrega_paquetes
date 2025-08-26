import re
import requests
import logging
from dataclasses import dataclass
from typing import Optional

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

    def validar_formato_pieza(self) -> bool:
        """Valida que el número de pieza tenga el formato correcto: 2 letras + 9 números + 2 letras"""
        patron = re.compile(r'^[A-Z]{2}\d{9}[A-Z]{2}$')
        return bool(patron.match(self.pieza))

    def es_valido(self) -> bool:
        """Verifica si los datos del paquete son válidos"""
        pieza_limpia = self.limpiar().pieza
        return self.validar_formato_pieza() and self.guarda.isdigit()

    def limpiar(self) -> 'DatosPaquete':
        """Limpia y formatea los datos del paquete"""
        pieza_limpia = re.sub(r'\W+$', '', self.pieza.replace(" ", "").upper())
        guarda_limpia = ''.join(filter(str.isdigit, self.guarda))
        return DatosPaquete(pieza_limpia, guarda_limpia)

class ServerCommunicator:
    """Clase para manejar la comunicación con el servidor"""
    def __init__(self, base_server_url: str):
        # Almacenar la URL base, sin endpoint específico al final
        self.server_url = base_server_url.rstrip('/') 

    def enviar_datos(self, datos: DatosPaquete) -> bool:
        """Envía los datos finales del paquete al servidor y retorna si fue exitoso"""
        # Usar la URL base + el endpoint específico para los datos finales
        target_url = f"{self.server_url}/pedido" 
        try:
            payload = {"pieza": datos.pieza, "guarda": datos.guarda}
            response = requests.post(target_url, json=payload, timeout=10) # Añadir timeout
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al enviar datos a {target_url}: {e}")
            print(f"Error al enviar datos a {target_url}: {e}")
            return False

    def enviar_imagenes(self, base64_pieza: str, base64_guarda: str) -> Optional[dict]:
        """Envía las imágenes codificadas en Base64 al servidor para su procesamiento OCR."""
        # Usar la URL base + el endpoint específico para el OCR
        target_url = f"{self.server_url}/procesarocr" 
        try:
            payload = {
                "imagen_pieza": base64_pieza,
                "imagen_guarda": base64_guarda
            }
            response = requests.post(target_url, json=payload, timeout=30) # Aumentar timeout para OCR
            response.raise_for_status()  # Lanza una excepción para errores HTTP (4xx o 5xx)
            
            datos_extraidos = response.json()
            print("Respuesta del servidor para OCR:", datos_extraidos)
            return datos_extraidos
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al enviar imágenes al servidor OCR a {target_url}: {e}")
            print(f"Error al enviar imágenes al servidor OCR a {target_url}: {e}")
            return None