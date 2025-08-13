# ENTREGA DE PAQUETES - PROTOTIPO

## Servidor

1. Entrar a la carpeta `server/`
2. Instalar dependencias:
   pip install -r requirements.txt
3. Ejecutar servidor:
   uvicorn main:app --host 0.0.0.0 --port 8000

## Cliente PC1 (Consulta)

1. Instalar dependencias:
   pip install -r requirements.txt
2. Instalar Tesseract OCR:
   Ejecutar `install_tesseract.bat` o instalarlo manualmente, instalar el language data para spanish, agregar el directorio al PATH
   https://github.com/UB-Mannheim/tesseract/wiki
4. Ejecutar app normalmente:
   python app.py
5. Presionar F4 luego de ingresar una pieza → se envía al servidor



## Cliente entrega/deposito
1. Para generar el ejecutable
   pyinstaller main.py --onefile --add-data "common.py;." --add-data "config_dialog.py;." --add-data "config.py;." --add-data "configuration_service.py;." --add-data "deposito/app.py;deposito" --add-data "entrega/app.py;entrega"
   #para que no abra la consola
   pyinstaller main.py --onefile --windowed --add-data "common.py;." --add-data "config_dialog.py;." --add-data "config.py;." --add-data "configuration_service.py;." --add-data "deposito/app.py;deposito" --add-data "entrega/app.py;entrega"
