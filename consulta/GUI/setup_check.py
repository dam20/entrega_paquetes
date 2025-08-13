#!/usr/bin/env python3
"""
Verificador de configuración para Consulta App
Verifica que todos los archivos y dependencias estén correctos
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

def check_python_version() -> bool:
    """Verifica la versión de Python"""
    if sys.version_info < (3, 8):
        print(f"❌ Python 3.8+ requerido. Versión actual: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True

def check_files() -> bool:
    """Verifica que todos los archivos necesarios existan"""
    required_files = [
        'app_gui.py',
        'config.py',
        'config_dialog.py', 
        'configuration_service.py',
        'run_app.py',
        'requirements.txt'
    ]
    
    script_dir = Path(__file__).parent
    missing_files = []
    existing_files = []
    
    print("\n📁 Verificando archivos:")
    for file_name in required_files:
        file_path = script_dir / file_name
        if file_path.exists():
            print(f"✅ {file_name}")
            existing_files.append(file_name)
        else:
            print(f"❌ {file_name} - FALTANTE")
            missing_files.append(file_name)
    
    if missing_files:
        print(f"\n❌ Faltan {len(missing_files)} archivos requeridos")
        return False
    
    print(f"\n✅ Todos los archivos presentes ({len(existing_files)}/{ len(required_files)})")
    return True

def check_dependencies() -> Tuple[bool, List[str]]:
    """Verifica las dependencias de Python"""
    dependencies = [
        ('PyQt5', 'PyQt5'),
        ('cv2', 'opencv-python'),
        ('numpy', 'numpy'),
        ('pytesseract', 'pytesseract'),
        ('requests', 'requests'),
        ('PIL', 'Pillow'),
        ('keyboard', 'keyboard')
    ]
    
    print("\n📦 Verificando dependencias:")
    installed = []
    missing = []
    
    for import_name, package_name in dependencies:
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
            installed.append(package_name)
        except ImportError:
            print(f"❌ {package_name} - NO INSTALADO")
            missing.append(package_name)
    
    success = len(missing) == 0
    
    if success:
        print(f"\n✅ Todas las dependencias instaladas ({len(installed)}/{len(dependencies)})")
    else:
        print(f"\n❌ Faltan {len(missing)} dependencias")
        print("\n💡 Para instalar las dependencias faltantes:")
        print("   pip install -r requirements.txt")
        print("\n   O instalar individualmente:")
        for pkg in missing:
            print(f"   pip install {pkg}")
    
    return success, missing

def check_tesseract() -> bool:
    """Verifica que Tesseract OCR esté instalado"""
    print("\n🔍 Verificando Tesseract OCR:")
    try:
        import pytesseract
        # Intentar obtener la versión
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract OCR v{version}")
        return True
    except Exception as e:
        print(f"❌ Tesseract OCR no disponible: {e}")
        print("\n💡 Instala Tesseract OCR:")
        print("   Windows: https://github.com/UB-Mannheim/tesseract/wiki")
        print("   Linux: sudo apt install tesseract-ocr")
        print("   macOS: brew install tesseract")
        return False

def create_sample_config() -> None:
    """Crea un archivo de configuración de ejemplo"""
    config_file = Path("config.json")
    if not config_file.exists():
        sample_config = {
            "ip": "localhost",
            "puerto": 8000
        }
        
        try:
            import json
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(sample_config, f, indent=4)
            print(f"✅ Archivo de configuración de ejemplo creado: {config_file}")
        except Exception as e:
            print(f"⚠️  No se pudo crear config.json: {e}")
    else:
        print("ℹ️  Archivo config.json ya existe")

def main() -> int:
    """Función principal del verificador"""
    print("🔍 Consulta App - Verificador de Configuración")
    print("=" * 50)
    
    all_good = True
    
    # Verificar Python
    if not check_python_version():
        all_good = False
    
    # Verificar archivos
    if not check_files():
        all_good = False
        return 1  # Sin archivos no podemos continuar
    
    # Verificar dependencias
    deps_ok, missing_deps = check_dependencies()
    if not deps_ok:
        all_good = False
    
    # Verificar Tesseract (solo si las dependencias están)
    if deps_ok:
        if not check_tesseract():
            all_good = False
    
    # Crear configuración de ejemplo
    print("\n⚙️ Configuración:")
    create_sample_config()
    
    # Resumen final
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 ¡Todo listo! Puedes ejecutar la aplicación con:")
        print("   python run_app.py")
        print("\nO directamente:")
        print("   python app_gui.py")
    else:
        print("❌ Hay problemas que resolver antes de ejecutar la aplicación")
        if missing_deps:
            print(f"\n🔧 Primero instala las dependencias faltantes:")
            print("   pip install -r requirements.txt")
    
    print("\n📚 Documentación de la app:")
    print("   • F4: Capturar pantalla")
    print("   • Doble click: Editar campos en ventana de confirmación") 
    print("   • Enter: Confirmar y enviar datos")
    print("   • System tray: Controles adicionales")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())
