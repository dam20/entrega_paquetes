import sys
from PyQt5.QtWidgets import QApplication
from gui import ConsultaApp
from configuration_service import ConfigurationService

def main():
    temp_app = QApplication.instance()
    if temp_app is None:
        temp_app = QApplication(sys.argv)

    config_service = ConfigurationService()
    
    if not config_service.ensure_configuration():
        print("❌ Configuración cancelada por el usuario")
        return 1
    
    server_url, _ = config_service.get_server_urls()
    
    if server_url is None:
        print("❌ Error: No se pudo obtener la configuración del servidor")
        return 1
    
    app = ConsultaApp(server_url, config_service)
    sys.exit(app.run())

if __name__ == "__main__":
    main()