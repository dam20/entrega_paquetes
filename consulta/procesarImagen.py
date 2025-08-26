import cv2
import numpy as np
import base64

def cortarImagen(imagen_array):
    """
    Corta la imagen detectando bordes grises claros.
    
    Parámetros:
    - imagen_array (numpy.ndarray): Array de la imagen de entrada
    
    Retorna:
    - numpy.ndarray: Imagen recortada o None si no se encuentra
    """
    if not isinstance(imagen_array, np.ndarray):
        raise ValueError("El input debe ser un numpy.ndarray")
    
    img = imagen_array.copy()
    
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

def encodeImagen(imagen_array):
    """
    Codifica una imagen en formato base64.
    
    Parámetros:
    - imagen_array (numpy.ndarray): Array de la imagen a codificar
    
    Retorna:
    - str: Imagen codificada en base64
    """
    _, buffer = cv2.imencode('.png', imagen_array)
    return base64.b64encode(buffer.tobytes()).decode('utf-8')

def procesarImagen(imagen_array):
    """
    Procesa una imagen para extraer las secciones de número de pieza y lugar de guarda.
    
    Parámetros:
    - imagen_array (numpy.ndarray): Array de la imagen de entrada
    
    Retorna:
    - tuple: Una tupla que contiene (nroPieza_bytes, lugarGuarda_bytes) o (None, None) si hay errores.
    """
    try:
        if not isinstance(imagen_array, np.ndarray):
            raise ValueError("El input debe ser un numpy.ndarray")
        
        print("=" * 60)
        print("🚀 INICIANDO PROCESAMIENTO DE IMAGEN PARA RECORTES")
        print("=" * 60)
        
        imagen_cortada = cortarImagen(imagen_array)
        
        if imagen_cortada is None:
            print("❌ No se pudo cortar la imagen principal. Retornando None, None.")
            return None, None
        
        print(f"📐 Imagen cortada principal: {imagen_cortada.shape}")
        
        nroPieza_img = None
        lugarGuarda_img = None

        try:
            # Recorte para el número de pieza
            nroPieza_img = cortarImagenPorcentual(imagen_cortada, 33.06, 2.5, 70.56, 8.87)
            print(f"📋 Campo número de pieza recortado: {nroPieza_img.shape}")
            nroPieza_bytes = encodeImagen(nroPieza_img)
            print(f"📋 Campo número de pieza codificado.")
        except Exception as e:
            print(f"❌ Error al recortar número de pieza: {e}")
            # Si hay un error, el recorte específico será None

        try:
            # Recorte para el lugar de guarda
            lugarGuarda_img = cortarImagenPorcentual(imagen_cortada, 33.06, 84.5, 68.25, 90.78)
            print(f"📍 Campo lugar de guarda recortado: {lugarGuarda_img.shape}")
            lugarGuarda_bytes = encodeImagen(lugarGuarda_img)
            print(f"📍 Campo lugar de guarda codificado.")
        except Exception as e:
            print(f"❌ Error al recortar lugar de guarda: {e}")
            # Si hay un error, el recorte específico será None

        return nroPieza_bytes, lugarGuarda_bytes

    except Exception as e:
        error_msg = f"Error general en procesarImagen: {str(e)}"
        print(f"❌ {error_msg}")
        return None, None
