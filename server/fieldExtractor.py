import cv2
import numpy as np
import easyocr
import json
import re
import logging

from validator import PiezaValidator, LugarGuardaValidator

# Configuración de logging
logging.basicConfig(
    filename='server_ocr.log',
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Inicializar EasyOCR una sola vez
try:
    EASYOCR_READER = easyocr.Reader(['es'], gpu=False)
    logging.info("EasyOCR Reader inicializado globalmente.")
except Exception as e:
    logging.error(f"Error al inicializar EasyOCR Reader: {e}", exc_info=True)
    EASYOCR_READER = None

def extraer_texto_easyocr(imagen_array) -> str:
    """
    Extrae texto de una imagen usando EasyOCR directamente.
    Sin preprocesamiento para imágenes de fondo blanco con texto negro.

    Parámetros:
    - imagen_array (numpy.ndarray): Array de la imagen de entrada

    Retorna:
    - str: Texto extraído
    """
    if EASYOCR_READER is None:
        logging.error("EasyOCR Reader no está inicializado.")
        return "Error: OCR engine no disponible"

    try:
        # Verificar imagen válida
        if imagen_array is None or imagen_array.size == 0:
            logging.warning("Imagen vacía o None recibida")
            return "Error: Imagen inválida"
            
        # EasyOCR directo - sin preprocesamiento para imágenes limpias
        results = EASYOCR_READER.readtext(
            imagen_array,
            detail=0,  # Solo texto, sin coordenadas
            paragraph=False,  # Línea por línea
            width_ths=0.7,  # Umbral para unir caracteres
            height_ths=0.7   # Umbral para unir líneas
        )
        
        # Unir texto detectado
        extracted_text = " ".join(results).strip() if results else ""
        logging.info(f"EasyOCR detectó: '{extracted_text}' ({len(results)} elementos)")
        
        return extracted_text
        
    except Exception as e:
        logging.error(f"Error en EasyOCR: {e}", exc_info=True)
        return f"Error: {str(e)}"

def procesar_numero_pieza_easyocr(imagen_array):
    """
    Procesa el campo de número de pieza con EasyOCR.
    """
    logging.info("🔍 Procesando número de pieza con EasyOCR...")
    
    texto_extraido = extraer_texto_easyocr(imagen_array)
    print(f"Pieza extraída: {texto_extraido}")
    
    if texto_extraido.startswith('Error:'):
        logging.warning(f"Error al extraer texto de pieza: {texto_extraido}")
        return texto_extraido
    
    # Corregir errores comunes del OCR
    texto_corregido = PiezaValidator.corregir_pieza_ocr(texto_extraido)
    
    # Validar formato final
    if PiezaValidator.validar_formato_completo(texto_corregido):
        logging.info(f"✅ Número de pieza válido: '{texto_corregido}'")
        return texto_corregido
    else:
        logging.warning(f"⚠️ Número de pieza formato incorrecto: '{texto_corregido}' (original: '{texto_extraido}')")
        return texto_corregido

def procesar_lugar_guarda_easyocr(imagen_array):
    """
    Procesa el campo de lugar de guarda con EasyOCR.
    """
    logging.info("📍 Procesando lugar de guarda con EasyOCR...")
    
    texto_extraido = extraer_texto_easyocr(imagen_array)
    print(f"Guarda extraída: {texto_extraido}")

    if texto_extraido.startswith('Error:'):
        logging.warning(f"Error al extraer texto de guarda: {texto_extraido}")
        return texto_extraido
    
    # Corregir y normalizar
    texto_corregido = LugarGuardaValidator.corregir_lugar_guarda_ocr(texto_extraido)
    texto_normalizado = texto_corregido
    #texto_normalizado = LugarGuardaValidator.normalizar_lugar_guarda(texto_corregido)
    
    if LugarGuardaValidator.validar_lugar_guarda(texto_normalizado):
        logging.info(f"✅ Lugar de guarda válido: '{texto_normalizado}' (original: '{texto_extraido}')")
        return texto_normalizado
    else:
        logging.warning(f"⚠️ Lugar de guarda formato incorrecto: '{texto_normalizado}' (original: '{texto_extraido}')")
        return texto_normalizado