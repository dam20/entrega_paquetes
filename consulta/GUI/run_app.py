#!/usr/bin/env python3
"""
Script simple para ejecutar la aplicación en modo desarrollo
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    # """Verifica que las dependencias estén instaladas"""
    # required_packages = [
    #     ('PySide6', 'PySide6'), 
    #     ('cv2', 'opencv-python'), 
    #     ('numpy', 'numpy'), 
    #     ('pytesseract', 'pytesseract'), 
    #     ('requests', 'requests'), 
    #     ('PIL', 'Pillow'), 
    #     ('keyboard', 'keyboard')
    # ]
    
    # missing_packages = []
    
    # for import_name, package_name in required_packages:
    #     try:
    #         __import__(import_name)
    #     except ImportError:
    #         missing_packages.append(package_name)
    
    # if missing_packages:
    #     print("❌ Faltan las siguientes dependencias:")
    #     for pkg in missing_packages:
    #         print(f"   - {pkg}")
    #     print("\n💡 Instálalas con: pip install -r requirements.txt")
    #     return False
    
    return True

def check_required_files():
    """Verifica que los archivos requeridos existan"""
    required_files = [
        'app_gui.py',
        'config.py', 
        'config_dialog.py',
        'configuration_service.py'
    ]
    
    script_dir = Path(__file__).parent
    missing_files = []
    
    for file_name in required_files:
        if not (script_dir / file_name).exists():
            missing_files.append(file_name)
    
    if missing_files:
        print("❌ Faltan los siguientes archivos requeridos:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    return True

def main():
    """Función principal"""
    print("🚀 Iniciando Consulta App...")
    
    # Verificar dependencias
    if not check_requirements():
        return 1
    
    # Verificar archivos requeridos
    if not check_required_files():
        return 1
    
    # Cambiar al directorio del script
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    try:
        # Ejecutar la aplicación principal
        from app_gui import main as app_main
        return app_main()
        
    except KeyboardInterrupt:
        print("\n👋 Aplicación cerrada por el usuario")
        return 0
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        print("💡 Asegúrate de que todos los archivos estén en el mismo directorio")
        return 1
    except Exception as e:
        print(f"❌ Error al ejecutar la aplicación: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())