import cv2
import numpy as np

# Cargar imagen
img = cv2.imread("consulta.png")

# Convertir a HSV para trabajar con matiz/saturación si se desea (opcional)
# hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# Definir el rango de gris (gris claro alrededor de RGB(160,160,160))
lower = np.array([150, 150, 150], dtype=np.uint8)
upper = np.array([170, 170, 170], dtype=np.uint8)

# Crear máscara para detectar el borde de color gris claro
mask = cv2.inRange(img, lower, upper)

# Limpiar ruido con morfología
kernel = np.ones((3, 3), np.uint8)
mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

# Buscar contornos
contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

found = False
for cnt in contours:
    approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
    area = cv2.contourArea(cnt)

    if len(approx) == 4 and area > 1000:
        x, y, w, h = cv2.boundingRect(approx)

        # Recortar sin los bordes (si el borde tiene 2px)
        cropped = img[y+2:y+h-2, x+2:x+w-2]
        cv2.imwrite("ventana_borde_gris.png", cropped)
        print("✅ Ventana recortada correctamente con borde gris.")
        found = True
        break

if not found:
    print("❌ No se encontró una ventana con borde gris claro.")
