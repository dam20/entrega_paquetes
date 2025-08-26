import keyboard
import time
from PyQt5.QtCore import QThread, pyqtSignal
# cv2 y base64 ya no son necesarios aquí si procesarImagen ya devuelve base64
# import cv2 
# import base64 
import requests # Necesario para la comunicación HTTP en el worker

class KeyboardWorker(QThread):
    """Worker thread para manejar la captura de teclas"""
    
    f4_pressed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.running = True
        self._stop_event = False

    def run(self):
        """Ejecuta el bucle de detección de teclas"""
        print("🎯 Detector de teclas iniciado (F4 para capturar)")
        last_f4_time = 0
        
        while self.running and not self._stop_event:
            try:
                if keyboard.is_pressed('f4'):
                    current_time = time.time()
                    if current_time - last_f4_time > 2.0:
                        self.f4_pressed.emit()
                        last_f4_time = current_time
                        
                time.sleep(0.1)
            except Exception as e:
                print(f"⚠️ Error en detección de teclas: {e}")
                time.sleep(1)

    def stop(self):
        """Detiene el worker"""
        print("🛑 Deteniendo detector de teclas...")
        self.running = False
        self._stop_event = True


class OcrRequestWorker(QThread):
    """
    Worker thread para manejar el envío de imágenes (Base64) al servidor para OCR
    y recibir la respuesta.
    """
    ocr_result = pyqtSignal(dict) # Emitirá el JSON con los datos extraídos
    ocr_error = pyqtSignal(str)   # Emitirá un mensaje de error

    # Recibe las cadenas Base64 directamente, ya que procesarImagen las genera
    def __init__(self, base64_pieza_str: str, base64_guarda_str: str, server_communicator):
        super().__init__()
        self.base64_pieza_str = base64_pieza_str
        self.base64_guarda_str = base64_guarda_str
        self.server_communicator = server_communicator

    def run(self):
        """
        Envía las imágenes (Base64) al servidor y emite el resultado.
        """
        try:
            print("💡 Enviando recortes al servidor para OCR desde el Worker...")
            # Llama directamente a enviar_imagenes del ServerCommunicator
            datos_extraidos = self.server_communicator.enviar_imagenes(self.base64_pieza_str, self.base64_guarda_str)
            
            if datos_extraidos:
                self.ocr_result.emit(datos_extraidos)
            else:
                # Si datos_extraidos es None, significa que hubo un error en la comunicación o respuesta del servidor
                self.ocr_error.emit("El servidor no devolvió datos válidos para OCR o hubo un error en la comunicación.")

        except Exception as e:
            error_msg = f"Error inesperado en OcrRequestWorker: {e}"
            print(f"❌ {error_msg}")
            self.ocr_error.emit(error_msg)

