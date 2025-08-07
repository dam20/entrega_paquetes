import cv2
import numpy as np
import pytesseract

# --- Cargar imagen completa y detectar ventana con borde gris ---
img = cv2.imread("consulta.png")

# Definir el color gris claro del borde
lower = np.array([150, 150, 150], dtype=np.uint8)
upper = np.array([170, 170, 170], dtype=np.uint8)

# Máscara para el borde gris
mask = cv2.inRange(img, lower, upper)

# Limpiar la máscara
kernel = np.ones((3, 3), np.uint8)
mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

# Buscar contornos (ventanas)
contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

ventana = None
for cnt in contours:
    approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
    area = cv2.contourArea(cnt)

    if len(approx) == 4 and area > 1000:
        x, y, w, h = cv2.boundingRect(approx)
        ventana = img[y+2:y+h-2, x+2:x+w-2]  # Recorte sin los 2px del borde
        break

# Verificar si se encontró la ventana
if ventana is None:
    print("❌ No se encontró ninguna ventana con borde gris.")
    exit()

# --- Comenzar OCR sobre el recorte (ventana) directamente ---
# ---------- CONFIGURACIÓN DE COLORES HEX ----------
def hex_to_bgr(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (4, 2, 0))  # BGR

# Color blanco del campo que queremos detectar
target_white = hex_to_bgr('#FFFFFF')

# Rango de tolerancia para blanco
tolerance = 5
lower_white = np.array([max(0, target_white[0]-tolerance),
                        max(0, target_white[1]-tolerance),
                        max(0, target_white[2]-tolerance)])
upper_white = np.array([min(255, target_white[0]+tolerance),
                        min(255, target_white[1]+tolerance),
                        min(255, target_white[2]+tolerance)])

# Crear máscara para detectar campos blancos
mask_white = cv2.inRange(ventana, lower_white, upper_white)

# Encontrar contornos de los campos blancos
contornos, _ = cv2.findContours(mask_white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Lista de resultados
resultados = []

for i, c in enumerate(contornos):
    x, y, w, h = cv2.boundingRect(c)
    if w > 30 and h > 10:
        # Recortar el campo directamente de la ventana original (no solo la máscara)
        campo = ventana[y:y+h, x:x+w]

        # OCR
        texto = pytesseract.image_to_string(campo, config='--psm 7').strip()
        if texto:
            resultados.append((y, x, texto))

# Ordenar resultados por posición
resultados.sort()

# Mostrar resultados
print("Campos detectados y texto extraído:\n")
for i, (_, _, texto) in enumerate(resultados, 1):
    print(f"[Campo {i}]: {texto}")

# Mostrar máscara (opcional)
cv2.imshow("Mascara Blanca", mask_white)
cv2.waitKey(0)
cv2.destroyAllWindows()
