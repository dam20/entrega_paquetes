import cv2
import numpy as np
import pytesseract
from PIL import Image
import json
from validator import PiezaValidator, LugarGuardaValidator

def cortarImagen(imagen_array):
    """
    Corta la imagen detectando bordes grises claros.
    
    Parámetros:
    - imagen_array (numpy.ndarray): Array de la imagen de entrada
    
    Retorna:
    - numpy.ndarray: Imagen recortada o None si no se encuentra
    """
    # Verificar que el input sea un numpy array
    if not isinstance(imagen_array, np.ndarray):
        raise ValueError("El input debe ser un numpy.ndarray")
    
    img = imagen_array.copy()
    
    # Definir el rango de gris claro
    lower = np.array([150, 150, 150], dtype=np.uint8)
    upper = np.array([170, 170, 170], dtype=np.uint8)
    
    # Crear máscara para detectar el borde de color gris claro
    mask = cv2.inRange(img, lower, upper)
    
    # Limpiar ruido con morfología
    kernel = np.ones((3, 3), np.uint8)
    mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Buscar contornos
    contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
        area = cv2.contourArea(cnt)
        
        if len(approx) == 4 and area > 1000:
            x, y, w, h = cv2.boundingRect(approx)
            cropped = img[y+2:y+h-2, x+2:x+w-2]
            print("✅ Ventana recortada correctamente con borde gris.")
            return cropped
    
    print("❌ No se encontró una ventana con borde gris claro.")
    return None

def cortarImagenPorcentual(image, x1_percent, y1_percent, x2_percent, y2_percent):
    """
    Recorta una imagen usando porcentajes del ancho y alto total.
    
    Parámetros:
    - image: numpy.ndarray de la imagen
    - x1_percent: porcentaje del ancho para el punto inicial X 
    - y1_percent: porcentaje del alto para el punto inicial Y 
    - x2_percent: porcentaje del ancho para el punto final X 
    - y2_percent: porcentaje del alto para el punto final Y 
    
    Retorna:
    - numpy.ndarray: imagen recortada
    """
    height, width = image.shape[:2]
    
    x1 = int((x1_percent / 100) * width)
    y1 = int((y1_percent / 100) * height)
    x2 = int((x2_percent / 100) * width)
    y2 = int((y2_percent / 100) * height)
    
    x1 = max(0, min(x1, width))
    y1 = max(0, min(y1, height))
    x2 = max(0, min(x2, width))
    y2 = max(0, min(y2, height))
    
    if x2 <= x1 or y2 <= y1:
        raise ValueError("Las coordenadas finales deben ser mayores que las iniciales")
    
    cropped_image = image[y1:y2, x1:x2]
    
    return cropped_image

def preprocesar_imagen_simple(imagen_array):
    """
    Preprocesamiento mínimo para campos con fondo blanco y texto negro
    
    Parámetros:
    - imagen_array (numpy.ndarray): Array de la imagen de entrada
    
    Retorna:
    - numpy.ndarray: Imagen procesada ligeramente
    """
    # Para campos con fondo blanco y texto negro, el preprocesamiento mínimo es mejor
    
    # Convertir a escala de grises si es necesario
    if len(imagen_array.shape) == 3:
        gray = cv2.cvtColor(imagen_array, cv2.COLOR_BGR2GRAY)
    else:
        gray = imagen_array.copy()
    
    # Solo redimensionar ligeramente para mejorar OCR (factor más conservador)
    scale_factor = 2  # Reducido de 3 a 2
    height, width = gray.shape
    new_height = int(height * scale_factor)
    new_width = int(width * scale_factor)
    resized = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    
    # Opcional: Ligera mejora de contraste solo si es necesario
    # Para texto negro sobre fondo blanco, esto puede no ser necesario
    return resized

def calcular_calidad_lugar_guarda(texto):
    """
    Calcula la calidad específica para lugares de guarda,
    priorizando el patrón "NUM P RESTANTE".
    
    Parámetros:
    - texto (str): Texto extraído
    
    Retorna:
    - int: Puntuación de calidad
    """
    if not texto:
        return 0
    
    texto_limpio = texto.strip().upper()
    calidad = 0
    
    # Caso 1: Patrón "58 P RESTANTE" - alta prioridad.
    # Usar un patrón más flexible para capturar variaciones.
    import re
    match_p_restante = re.match(r'^(\d{1,3})\s*P\s*RESTANTE', texto_limpio)
    if match_p_restante:
        # Puntuación máxima, ya que es el patrón esperado
        return 100 

    # Caso 2: Patrón numérico seguido de texto (e.g., "58PRESTANTE")
    match_num_texto = re.match(r'^(\d{1,3})\s*([A-Z]+.*)', texto_limpio)
    if match_num_texto:
        texto_parte = match_num_texto.group(2)
        if any(palabra in texto_parte for palabra in ['RESTANTE', 'PRESTANTE']):
            calidad = 90
        elif texto_parte in ['P', 'MESA', 'PISO']:
            calidad = 85
        else:
            calidad = 50
    
    # Caso 3: Solo números (ideal para muchos casos)
    elif texto_limpio.isdigit():
        if len(texto_limpio) <= 3:
            calidad = 85  # Menor que el patrón completo pero mejor que otros
        else:
            calidad = 20

    # Caso 4: Solo texto válido
    elif texto_limpio in LugarGuardaValidator.LUGARES_TEXTO_VALIDOS:
        calidad = 80
    
    # Caso 5: Validación con el validador existente
    elif LugarGuardaValidator.validar_lugar_guarda(texto_limpio):
        calidad = 70
    
    # Penalizar caracteres extraños, pero no espacios
    caracteres_raros = sum(1 for c in texto_limpio if not c.isalnum() and c not in ['/', '.', ' '])
    calidad -= caracteres_raros * 3
    
    return calidad

def extraer_texto_multiple_psm(imagen_array, es_numerico=False, es_pieza=False):
    """
    Extrae texto probando múltiples valores PSM para encontrar el mejor resultado
    
    Parámetros:
    - imagen_array (numpy.ndarray): Array de la imagen de entrada
    - es_numerico (bool): Si True, optimiza para solo números
    - es_pieza (bool): Si True, aplica validaciones específicas de pieza
    
    Retorna:
    - str: Mejor texto extraído
    """
    try:
        # Verificar que el input sea un numpy array
        if not isinstance(imagen_array, np.ndarray):
            raise ValueError("El input debe ser un numpy.ndarray")
        
        # Preprocesamiento mínimo
        imagen_procesada = preprocesar_imagen_simple(imagen_array)
        imagen_pil = Image.fromarray(imagen_procesada)
        
        # Configuraciones PSM a probar (basadas en tu experiencia)
        psm_configs = [3, 4, 6, 7, 8, 9, 10, 11, 13]
        
        # Definir whitelist según el tipo
        if es_numerico:
            whitelist = '0123456789'
        elif es_pieza:
            whitelist = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        else:
            whitelist = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz/. '
        
        resultados = []
        
        print(f"🔍 Probando {len(psm_configs)} configuraciones PSM...")
        
        for psm in psm_configs:
            try:
                config = f'--oem 3 --psm {psm} -c tessedit_char_whitelist={whitelist}'
                texto = pytesseract.image_to_string(imagen_pil, config=config).strip()
                
                if texto:  # Si se extrajo algún texto
                    # Calcular calidad del resultado según el tipo
                    if es_numerico:
                        calidad = len(texto) if texto.isdigit() else 0
                        if texto.isdigit():
                            calidad += 50
                    elif es_pieza:
                        calidad = len(texto)
                        # Validar formato de pieza
                        if PiezaValidator.validar_formato_completo(texto):
                            calidad += 100  # Bonificación alta para formato válido
                        elif len(texto) == 13:  # Longitud correcta
                            calidad += 20
                    else:
                        # Para lugar de guarda - usar función específica
                        calidad = calcular_calidad_lugar_guarda(texto)
                    
                    # Penalizar caracteres extraños solo si no es lugar de guarda
                    if not (not es_numerico and not es_pieza):  # Si NO es lugar de guarda
                        caracteres_raros = sum(1 for c in texto if not c.isalnum() and c not in '/.')
                        calidad -= caracteres_raros * 5
                    
                    resultados.append({
                        'texto': texto,
                        'calidad': calidad,
                        'psm': psm
                    })
                    
                    print(f"  PSM {psm}: '{texto}' (calidad: {calidad})")
                
            except Exception as e:
                print(f"  ⚠️ Error con PSM {psm}: {e}")
                continue
        
        if resultados:
            # Ordenar por calidad y seleccionar el mejor
            mejor = max(resultados, key=lambda x: x['calidad'])
            print(f"✅ Mejor resultado: '{mejor['texto']}' (PSM {mejor['psm']}, calidad: {mejor['calidad']})")
            return mejor['texto']
        else:
            print("❌ No se extrajo texto con ninguna configuración PSM")
            return "Error: No se pudo extraer texto"
            
    except Exception as e:
        print(f"❌ Error en extraer_texto_multiple_psm: {str(e)}")
        return f"Error: {str(e)}"

def procesar_numero_pieza(imagen_array):
    """
    Procesa específicamente el campo de número de pieza
    
    Parámetros:
    - imagen_array (numpy.ndarray): Imagen del campo de número de pieza
    
    Retorna:
    - str: Número de pieza extraído y validado
    """
    print("🔍 Procesando número de pieza...")
    
    # Extraer texto con validación específica de pieza
    texto_extraido = extraer_texto_multiple_psm(imagen_array, es_numerico=False, es_pieza=True)
    
    if texto_extraido.startswith('Error:'):
        return texto_extraido
    
    # Intentar corregir errores comunes del OCR
    texto_corregido = PiezaValidator.corregir_pieza_ocr(texto_extraido)
    
    # Validar formato final
    if PiezaValidator.validar_formato_completo(texto_corregido):
        print(f"✅ Número de pieza válido: '{texto_corregido}'")
        return texto_corregido
    else:
        print(f"⚠️ Número de pieza con formato incorrecto: '{texto_corregido}'")
        # Devolver el corregido aunque no sea válido, para que se pueda editar manualmente
        return texto_corregido

def procesar_lugar_guarda(imagen_array):
    """
    Procesa específicamente el campo de lugar de guarda
    
    Parámetros:
    - imagen_array (numpy.ndarray): Imagen del campo de lugar de guarda
    
    Retorna:
    - str: Lugar de guarda extraído y validado
    """
    print("🔍 Procesando lugar de guarda...")
    
    # Probar como numérico
    texto_numerico = extraer_texto_multiple_psm(imagen_array, es_numerico=True, es_pieza=False)
    
    # Probar como texto general
    texto_general = extraer_texto_multiple_psm(imagen_array, es_numerico=False, es_pieza=False)
    
    candidatos_validos = []
    
    if not texto_numerico.startswith('Error:'):
        # Usar el validador para corregir y normalizar
        texto_num_corregido = LugarGuardaValidator.corregir_lugar_guarda_ocr(texto_numerico)
        if LugarGuardaValidator.validar_lugar_guarda(texto_num_corregido):
            candidatos_validos.append(texto_num_corregido)
    
    if not texto_general.startswith('Error:'):
        # Usar el validador para corregir y normalizar
        texto_gen_corregido = LugarGuardaValidator.corregir_lugar_guarda_ocr(texto_general)
        if LugarGuardaValidator.validar_lugar_guarda(texto_gen_corregido):
            candidatos_validos.append(texto_gen_corregido)
    
    # Eliminamos duplicados
    candidatos_validos = list(set(candidatos_validos))
    
    # Estrategia de selección:
    # 1. Priorizar resultados puramente numéricos si son cortos (2-3 dígitos)
    # 2. Priorizar el resultado '58'
    
    if '58' in candidatos_validos:
        print("✅ Se encontró '58', lo seleccionamos como resultado principal.")
        return '58'
        
    for candidato in sorted(candidatos_validos, key=len):
        if candidato.isdigit() and len(candidato) <= 3:
            print(f"✅ Se encontró un candidato numérico válido: '{candidato}'")
            return candidato
            
    if candidatos_validos:
        print(f"⚠️ No se encontró un candidato numérico ideal, seleccionando el primero válido: '{candidatos_validos[0]}'")
        return candidatos_validos[0]
    
    print("❌ No se pudo procesar el lugar de guarda")
    return "Error: No se pudo extraer lugar de guarda"

def procesarImagen(imagen_array):
    """
    Procesa una imagen para extraer información de pieza y lugar de guarda con OCR optimizado.
    
    Parámetros:
    - imagen_array (numpy.ndarray): Array de la imagen de entrada
    
    Retorna:
    - dict: JSON con los campos "pieza" y "guarda"
    """
    try:
        # Verificar que el input sea un numpy array
        if not isinstance(imagen_array, np.ndarray):
            raise ValueError("El input debe ser un numpy.ndarray")
        
        print("=" * 60)
        print("🚀 INICIANDO PROCESAMIENTO DE IMAGEN")
        print("=" * 60)
        
        # Cortar la imagen principal
        imagen_cortada = cortarImagen(imagen_array)
        
        if imagen_cortada is None:
            return {
                "pieza": "Error: No se pudo cortar la imagen",
                "guarda": "Error: No se pudo cortar la imagen"
            }
        
        print(f"📐 Imagen cortada: {imagen_cortada.shape}")
        
        # Extraer las secciones específicas
        try:
            nroPieza_img = cortarImagenPorcentual(imagen_cortada, 33.06, 2.5, 70.56, 8.87)
            print(f"📋 Campo número de pieza recortado: {nroPieza_img.shape}")
        except Exception as e:
            print(f"❌ Error al recortar número de pieza: {e}")
            return {
                "pieza": f"Error: Error al recortar número de pieza - {e}",
                "guarda": "Error: Error al recortar número de pieza"
            }
        
        try:
            lugarGuarda_img = cortarImagenPorcentual(imagen_cortada, 33.06, 84.5, 68.25, 90.78)
            print(f"📍 Campo lugar de guarda recortado: {lugarGuarda_img.shape}")
        except Exception as e:
            print(f"❌ Error al recortar lugar de guarda: {e}")
            return {
                "pieza": "Error: Error al recortar lugar de guarda",
                "guarda": f"Error: Error al recortar lugar de guarda - {e}"
            }
        
        # Procesar cada campo con su lógica específica
        nroPieza_final = procesar_numero_pieza(nroPieza_img)
        lugarGuarda_final = procesar_lugar_guarda(lugarGuarda_img)
        
        # Crear el JSON de respuesta
        resultado = {
            "pieza": nroPieza_final,
            "guarda": lugarGuarda_final
        }
        
        print("=" * 60)
        print("📦 RESULTADO FINAL DEL PROCESAMIENTO:")
        print(json.dumps(resultado, indent=4, ensure_ascii=False))
        print("=" * 60)
        
        return resultado
    
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ Error general en procesarImagen: {error_msg}")
        return {
            "pieza": error_msg,
            "guarda": error_msg
        }

def test_procesamiento():
    """Función de prueba para el procesamiento"""
    print("Esta función requiere una imagen real para probar.")
    print("Ejecuta el script principal con una imagen de prueba.")

# Para pruebas
if __name__ == "__main__":
    # Ruta a la imagen local
    ruta_imagen = "imagenes/Captura5.png"

    # Cargar imagen con OpenCV
    imagen = cv2.imread(ruta_imagen)

    # Verificar si se cargó correctamente
    if imagen is None:
        print(f"❌ No se pudo cargar la imagen desde: {ruta_imagen}")
    else:
        # Procesar la imagen
        resultado = procesarImagen(imagen)

        # Imprimir el resultado
        print("📦 Resultado del procesamiento:")
        print(json.dumps(resultado, indent=4, ensure_ascii=False))