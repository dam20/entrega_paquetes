import cv2
import numpy as np
import pytesseract

#pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Leer imagen
image = cv2.imread('consulta.png')

# ---------- CONFIGURACIÓN DE COLORES HEX ----------
def hex_to_bgr(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (4, 2, 0))  # BGR

# Color blanco del campo que queremos detectar
target_white = hex_to_bgr('#FFFFFF')

# Color gris claro del fondo que queremos evitar
gray_form_bg = hex_to_bgr('#F0F0F0')  # Ajustado según tu input

# ---------- MÁSCARA DE COLOR PRECISA ----------
# Rango de tolerancia para blanco
tolerance = 5

# Rango para blanco deseado
lower_white = np.array([max(0, target_white[0]-tolerance),
                        max(0, target_white[1]-tolerance),
                        max(0, target_white[2]-tolerance)])
upper_white = np.array([min(255, target_white[0]+tolerance),
                        min(255, target_white[1]+tolerance),
                        min(255, target_white[2]+tolerance)])

# Crear máscara para campos blancos
mask_white = cv2.inRange(image, lower_white, upper_white)



# Encontrar contornos
contornos, _ = cv2.findContours(mask_white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Lista para guardar resultados
resultados = []

# Filtrar y recorrer contornos
for i, c in enumerate(contornos):
    x, y, w, h = cv2.boundingRect(c)

    # Filtrar por tamaño mínimo razonable
    if w > 30 and h > 10:
        # Recortar campo
        campo = mask_white[y:y+h, x:x+w]

        # Aplicar OCR
        texto = pytesseract.image_to_string(campo, config='--psm 7').strip()

        if texto:
            resultados.append((y, x, texto))  # para ordenar después

# Ordenar por coordenadas (primero Y, luego X)
resultados.sort()

# Mostrar resultados
print("Campos detectados y texto extraído:\n")
for i, (_, _, texto) in enumerate(resultados, 1):
    print(f"[Campo {i}]: {texto}")



cv2.imshow("Mascara Blanca", mask_white)
cv2.waitKey(0)
cv2.destroyAllWindows()