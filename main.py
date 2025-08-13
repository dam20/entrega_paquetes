import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, 
    QLabel, QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from configuration_service import ConfigurationService


class SectorSelector(QWidget):
    """Selector de sector con integración de configuración"""
    
    def __init__(self):
        super().__init__()
        self.config_service = ConfigurationService()
        self._setup_ui()
        self._ensure_configuration()

    def _setup_ui(self) -> None:
        """Configura la interfaz de usuario"""
        self.setWindowTitle("Gestión de Pedidos - Selección de Sector")
        self.setFixedSize(350, 200)
        self._center_window()
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título principal
        title = QLabel("Sistema de Gestión de Pedidos")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Subtítulo
        subtitle = QLabel("Seleccione el sector:")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle.setFont(subtitle_font)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Botones de sector
        self._create_sector_buttons(layout)
        
    def _create_sector_buttons(self, layout: QVBoxLayout) -> None:
        """Crea los botones de selección de sector"""
        button_style = """
            QPushButton {
                font-size: 12pt; 
                padding: 2px; 
                border-radius: 8px;
                background-color: #3498db;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """
        
        # Botón Depósito
        self.btn_deposito = QPushButton("📦 Depósito")
        self.btn_deposito.setStyleSheet(button_style)
        self.btn_deposito.clicked.connect(self._open_deposito)
        layout.addWidget(self.btn_deposito)
        
        # Botón Entrega
        self.btn_entrega = QPushButton("🚚 Entrega")
        self.btn_entrega.setStyleSheet(button_style)
        self.btn_entrega.clicked.connect(self._open_entrega)
        layout.addWidget(self.btn_entrega)

    def _center_window(self) -> None:
        """Centra la ventana en la pantalla"""
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )

    def _ensure_configuration(self) -> None:
        """Asegura que la aplicación esté configurada"""
        if not self.config_service.ensure_configuration(self):
            self._show_exit_message()
            sys.exit(0)
        else:
            self._update_ui_with_config_status()

    def _update_ui_with_config_status(self) -> None:
        """Actualiza la UI con el estado de la configuración"""
        if self.config_service.is_configured():
            server_url, _ = self.config_service.get_server_urls()
            if server_url:
                # Extraer IP y puerto para mostrar
                url_parts = server_url.replace('http://', '').rstrip('/')
                self.setWindowTitle(f"Gestión de Pedidos - Conectado a: {url_parts}")

    def _show_config_dialog(self) -> None:
        """Muestra el diálogo de configuración"""
        if self.config_service.show_configuration_dialog(self):
            self._update_ui_with_config_status()
            QMessageBox.information(
                self, 
                "Configuración", 
                "Configuración actualizada correctamente."
            )

    def _show_exit_message(self) -> None:
        """Muestra mensaje de salida por falta de configuración"""
        QMessageBox.critical(
            self,
            "Configuración Requerida",
            "La aplicación necesita ser configurada para funcionar.\n"
            "No se puede continuar sin configuración del servidor."
        )

    def _open_deposito(self) -> None:
        """Abre la aplicación de depósito"""
        if not self._validate_configuration():
            return
            
        try:
            # Importación tardía para evitar problemas de dependencias circulares
            from deposito.app import DepositoApp
            
            server_url, ws_url = self.config_service.get_server_urls()
            self.close()
            self.deposito_window = DepositoApp(server_url, ws_url)
            self.deposito_window.show()
            
        except ImportError as e:
            self._show_import_error("Depósito", str(e))
        except Exception as e:
            self._show_general_error("Error al abrir Depósito", str(e))

    def _open_entrega(self) -> None:
        """Abre la aplicación de entrega"""
        if not self._validate_configuration():
            return
            
        try:
            # Importación tardía para evitar problemas de dependencias circulares
            from entrega.app import EntregaApp
            
            server_url, ws_url = self.config_service.get_server_urls()
            self.close()
            self.entrega_window = EntregaApp(server_url, ws_url)
            self.entrega_window.show()
            
        except ImportError as e:
            self._show_import_error("Entrega", str(e))
        except Exception as e:
            self._show_general_error("Error al abrir Entrega", str(e))

    def _validate_configuration(self) -> bool:
        """Valida que la configuración esté disponible"""
        if not self.config_service.is_configured():
            QMessageBox.warning(
                self,
                "Configuración Requerida",
                "Debe configurar el servidor antes de continuar.\n"
                "Use el botón 'Configurar Servidor'."
            )
            return False
        return True

    def _show_import_error(self, module_name: str, error: str) -> None:
        """Muestra error de importación de módulos"""
        QMessageBox.critical(
            self,
            f"Error de Módulo - {module_name}",
            f"No se pudo cargar el módulo {module_name}:\n{error}\n\n"
            f"Verifique que el módulo esté disponible."
        )

    def _show_general_error(self, title: str, error: str) -> None:
        """Muestra error general"""
        QMessageBox.critical(self, title, f"{error}")


def main():
    """Función principal de la aplicación"""
    app = QApplication(sys.argv)
    
    # Configurar la aplicación
    app.setApplicationName("Sistema de Gestión de Pedidos")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Empresa")
    
    try:
        selector = SectorSelector()
        selector.show()
        sys.exit(app.exec_())
        
    except Exception as e:
        QMessageBox.critical(
            None,
            "Error Fatal",
            f"Error al iniciar la aplicación:\n{e}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()