# ENTREGA DE PAQUETES - PROTOTIPO

## Servidor

1. Entrar a la carpeta `server/`
2. Instalar dependencias:
   pip install -r requirements.txt
3. Ejecutar servidor:
   uvicorn main:app --host 0.0.0.0 --port 8000

## Cliente PC1 (Consulta)

1. Instalar dependencias:
   pip install pytesseract pyautogui pillow keyboard requests
2. Instalar Tesseract OCR:
   Ejecutar `install_tesseract.bat` o instalarlo manualmente, agregar el directorio al PATH
3. Calibrar zonas:
   python app.py --calibrate
4. Ejecutar app normalmente:
   python app.py
5. Presionar F9 luego de ingresar una pieza → se envía al servidor
