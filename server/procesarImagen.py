import cv2
import numpy as np
import logging

# Importamos los validadores y las nuevas funciones de extracción para EasyOCR
from validator import PiezaValidator, LugarGuardaValidator
from fieldExtractor import procesar_numero_pieza_easyocr, procesar_lugar_guarda_easyocr


# Configuración de logging para este módulo
logging.basicConfig(
    filename='server_ocr.log',
    level=logging.INFO, # Nivel de logging corregido a INFO
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def preprocesar_ocr(imagen):
    # Aumentar tamaño (x4) con interpolación adecuada para texto
    escala = 4
    return cv2.resize(imagen, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)

def extraer_datos_ocr(img_pieza: np.ndarray, img_guarda: np.ndarray) -> tuple[str, str, bool]:
    """
    Realiza el OCR en las imágenes de pieza y guarda y devuelve el texto extraído
    utilizando EasyOCR y la lógica de procesamiento específica.

    Args:
        img_pieza (np.ndarray): Imagen de OpenCV (NumPy array) del número de pieza.
        img_guarda (np.ndarray): Imagen de OpenCV (NumPy array) del lugar de guarda.

    Returns:
        tuple[str, str]: Tupla con (texto_pieza, texto_guarda).
        Retorna cadenas vacías si la extracción falla.
    """
    texto_pieza = ""
    texto_guarda = ""
    poste_restante = False

    img_pieza = preprocesar_ocr(img_pieza)
    img_guarda = preprocesar_ocr(img_guarda)

    # El lector de EasyOCR se inicializará dentro de las funciones de fieldExtractor
    # para asegurar que los modelos se carguen correctamente por única vez o de manera eficiente.

    try:
        logging.info("Iniciando extracción OCR de la imagen de pieza con EasyOCR.")
        # Llamamos a la función dedicada para procesar la pieza con EasyOCR
        texto_pieza = procesar_numero_pieza_easyocr(img_pieza)
        logging.info(f"EasyOCR - Pieza: '{texto_pieza}'")

    except Exception as e:
        logging.error(f"Error al procesar OCR de 'pieza' con EasyOCR: {e}", exc_info=True)
        texto_pieza = f"Error: {e}" # Indicar error si falla el OCR de pieza

    try:
        logging.info("Iniciando extracción OCR de la imagen de guarda con EasyOCR.")
        # Llamamos a la función dedicada para procesar el lugar de guarda con EasyOCR
        texto_guarda, poste_restante = procesar_lugar_guarda_easyocr(img_guarda)

        logging.info(f"EasyOCR - Guarda: '{texto_guarda}' (poste restante: {poste_restante})")

    except Exception as e:
        logging.error(f"Error al procesar OCR de 'guarda' con EasyOCR: {e}", exc_info=True)
        texto_guarda = f"Error: {e}" # Indicar error si falla el OCR de guarda

    return texto_pieza, texto_guarda, poste_restante
