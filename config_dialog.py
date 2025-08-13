from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFormLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import requests
from typing import Tuple, Optional


class ConfigurationDialog(QDialog):
    """Diálogo para configurar la conexión del servidor"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()
        
    def _setup_ui(self) -> None:
        """Configura la interfaz de usuario"""
        self.setWindowTitle("Configuración del Servidor")
        self.setFixedSize(400, 200)
        self.setModal(True)
        self._center_window()
        
        # Layout principal
        layout = QVBoxLayout(self)
        
        # Título
        title_label = QLabel("Configuración de Conexión")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Formulario
        form_layout = QFormLayout()
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("localhost o 192.168.1.100")
        self.ip_input.setText("localhost")  # Valor por defecto
        form_layout.addRow("IP del Servidor:", self.ip_input)
        
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("8000")
        self.port_input.setText("8000")  # Valor por defecto
        form_layout.addRow("Puerto:", self.port_input)
        
        layout.addLayout(form_layout)
        
        # Botones
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("Probar Conexión")
        self.save_button = QPushButton("Guardar")
        self.cancel_button = QPushButton("Cancelar")
        
        button_layout.addWidget(self.test_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Estado inicial de botones
        self.save_button.setEnabled(False)
        
    def _setup_connections(self) -> None:
        """Configura las conexiones de señales"""
        self.test_button.clicked.connect(self._test_connection)
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        # Habilitar botón de prueba cuando hay texto
        self.ip_input.textChanged.connect(self._on_input_changed)
        self.port_input.textChanged.connect(self._on_input_changed)
        
    def _center_window(self) -> None:
        """Centra la ventana en la pantalla"""
        if self.parent():
            parent_rect = self.parent().geometry()
            self.move(
                parent_rect.center().x() - self.width() // 2,
                parent_rect.center().y() - self.height() // 2
            )
        
    def _on_input_changed(self) -> None:
        """Maneja cambios en los campos de entrada"""
        has_ip = bool(self.ip_input.text().strip())
        has_port = bool(self.port_input.text().strip())
        self.test_button.setEnabled(has_ip and has_port)
        
    def _test_connection(self) -> None:
        """Prueba la conexión con el servidor"""
        ip, port = self._get_input_values()
        
        if not self._validate_inputs(ip, port):
            return
            
        self.test_button.setEnabled(False)
        self.test_button.setText("Probando...")
        
        try:
            url = f"http://{ip}:{port}/health"  # Endpoint de salud
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                self._show_success_message("Conexión exitosa")
                self.save_button.setEnabled(True)
            else:
                self._show_error_message("El servidor no responde correctamente")
                
        except requests.exceptions.RequestException as e:
            self._show_error_message(f"Error de conexión: {str(e)}")
            
        finally:
            self.test_button.setEnabled(True)
            self.test_button.setText("Probar Conexión")
            
    def _validate_inputs(self, ip: str, port: str) -> bool:
        """Valida las entradas del usuario"""
        if not ip:
            self._show_error_message("La IP no puede estar vacía")
            return False
            
        if not port:
            self._show_error_message("El puerto no puede estar vacío")
            return False
            
        try:
            port_int = int(port)
            if not (1 <= port_int <= 65535):
                self._show_error_message("El puerto debe estar entre 1 y 65535")
                return False
        except ValueError:
            self._show_error_message("El puerto debe ser un número válido")
            return False
            
        return True
        
    def _get_input_values(self) -> Tuple[str, str]:
        """Obtiene los valores de entrada limpiados"""
        return (
            self.ip_input.text().strip(),
            self.port_input.text().strip()
        )
        
    def _show_success_message(self, message: str) -> None:
        """Muestra un mensaje de éxito"""
        QMessageBox.information(self, "Éxito", message)
        
    def _show_error_message(self, message: str) -> None:
        """Muestra un mensaje de error"""
        QMessageBox.warning(self, "Error", message)
        
    def get_configuration(self) -> Optional[Tuple[str, int]]:
        """Obtiene la configuración ingresada por el usuario"""
        ip, port = self._get_input_values()
        
        if self._validate_inputs(ip, port):
            return ip, int(port)
            
        return None