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
    #     'PySide6', 'opencv-python', 'numpy', 'pytesseract', 
    #     'requests', 'Pillow', 'keyboard'
    # ]
    
    # missing_packages = []
    
    # for package in required_packages:
    #     try:
    #         __import__(package.replace('-', '_').split('==')[0])
    #     except ImportError:
    #         missing_packages.append(package)
    
    # if missing_packages:
    #     print("❌ Faltan las siguientes dependencias:")
    #     for pkg in missing_packages:
    #         print(f"   - {pkg}")
    #     print("\n💡 Instálalas con: pip install -r requirements.txt")
    #     return False
    
    return True

def main():
    """Función principal"""
    print("🚀 Iniciando Consulta App...")
    
    # Verificar dependencias
    if not check_requirements():
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
    except Exception as e:
        print(f"❌ Error al ejecutar la aplicación: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())