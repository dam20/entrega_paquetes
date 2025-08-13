import sys
import requests
import json
import time
import threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QFrame, QSizePolicy,
    QScrollArea, QMessageBox
)
from PyQt5.QtCore import QObject, QThread, pyqtSignal as Signal, pyqtSlot as Slot, Qt
from websocket import WebSocketApp
from typing import Optional


class WebSocketWorker(QObject):
    """Trabajador para manejar conexiones WebSocket"""
    pedido_recibido = Signal(dict)
    connection_error = Signal(str)

    def __init__(self, ws_url: str):
        super().__init__()
        self.ws_url = ws_url
        self.ws = None
        self._should_run = True

    @Slot()
    def run_forever(self):
        """Ejecuta el WebSocket en un bucle con reconexión automática"""
        print("Iniciando hilo de WebSocket...")
        while self._should_run:
            try:
                self.ws = WebSocketApp(
                    self.ws_url,
                    on_message=self._on_message,
                    on_close=self._on_close,
                    on_error=self._on_error
                )
                self.ws.run_forever()
            except Exception as e:
                error_msg = f"WS desconectado: {e}"
                print(f"⚠️ {error_msg}. Reintentando en 5 segundos...")
                self.connection_error.emit(error_msg)
                if self._should_run:
                    time.sleep(5)

    def _on_message(self, ws, message):
        """Maneja mensajes recibidos del WebSocket"""
        try:
            data = json.loads(message)
            self.pedido_recibido.emit(data)
        except Exception as e:
            print(f"❌ Error procesando mensaje WebSocket: {e}")

    def _on_close(self, ws, close_status_code, close_msg):
        """Maneja el cierre del WebSocket"""
        print(f"WS cerrado con estado {close_status_code}: {close_msg}")

    def _on_error(self, ws, error):
        """Maneja errores del WebSocket"""
        error_msg = f"Error en WebSocket: {error}"
        print(f"❌ {error_msg}")
        self.connection_error.emit(error_msg)

    def stop(self):
        """Detiene el worker"""
        self._should_run = False
        if self.ws:
            self.ws.close()


class BaseApp(QMainWindow):
    """Aplicación base que proporciona funcionalidad común"""
    
    def __init__(self, titulo: str, server_url: str, ws_url: str, show_guarda: bool = True):
        """
        Inicializa la aplicación base.
        
        Args:
            titulo: Título de la ventana
            server_url: URL del servidor HTTP
            ws_url: URL del WebSocket
            show_guarda: Indica si se debe mostrar el número de guarda
        """
        super().__init__()
        
        self.server_url = server_url
        self.ws_url = ws_url
        self.show_guarda = show_guarda
        self.pedidos = {}
        self.widgets = {}
        
        self._setup_ui(titulo)
        self._load_existing_orders()
        self._setup_websocket()
        self._update_ui()

    def _setup_ui(self, titulo: str) -> None:
        """Configura la interfaz de usuario"""
        self.setWindowTitle(titulo)
        
        # Configuración de pantalla y dimensiones
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        available_geometry = screen.availableGeometry()
        
        # Cálculos de dimensiones
        title_bar_height = 32
        window_width = min(230, int(screen_geometry.width() * 0.25))
        window_height = available_geometry.height() - title_bar_height
        font_scale = min(1.0, screen_geometry.width() / 1024)
        
        self.font_scale = font_scale
        
        # Configuración del widget central
        self._setup_central_widget()
        self._setup_scroll_area(font_scale)
        self._setup_window_properties(window_width, window_height, available_geometry)

    def _setup_central_widget(self) -> None:
        """Configura el widget central"""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

    def _setup_scroll_area(self, font_scale: float) -> None:
        """Configura el área de desplazamiento"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Estilos del scroll area
        scroll_area.setStyleSheet(self._get_scroll_area_styles(font_scale))

        # Contenedor para los widgets de pedidos
        content_widget = QWidget()
        self.layout = QVBoxLayout(content_widget)
        
        spacing = max(2, int(3 * font_scale))
        margins = max(2, int(3 * font_scale))
        
        self.layout.setSpacing(spacing)
        self.layout.setContentsMargins(margins, margins, margins, margins)

        scroll_area.setWidget(content_widget)
        self.main_layout.addWidget(scroll_area)

    def _get_scroll_area_styles(self, font_scale: float) -> str:
        """Obtiene los estilos para el área de desplazamiento"""
        return f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                border: none;
                background: #f0f0f0;
                width: {int(8 * font_scale)}px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #c1c1c1;
                min-height: {int(25 * font_scale)}px;
                border-radius: {int(4 * font_scale)}px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
        """

    def _setup_window_properties(self, width: int, height: int, available_geometry) -> None:
        """Configura las propiedades de la ventana"""
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        self.setFixedWidth(width)
        self.setFixedHeight(height)
        
        # Posicionamiento en el borde derecho
        self.move(
            available_geometry.right() - width,
            available_geometry.top()
        )

    def _setup_websocket(self) -> None:
        """Configura la conexión WebSocket"""
        self.ws_thread = QThread()
        self.ws_worker = WebSocketWorker(self.ws_url)
        self.ws_worker.moveToThread(self.ws_thread)

        # Conexiones de señales
        self.ws_worker.pedido_recibido.connect(self.handle_nuevo_pedido)
        self.ws_worker.connection_error.connect(self._handle_connection_error)
        self.ws_thread.started.connect(self.ws_worker.run_forever)
        
        self.ws_thread.start()

    def _handle_connection_error(self, error_msg: str) -> None:
        """Maneja errores de conexión del WebSocket"""
        print(f"Error de conexión: {error_msg}")
        # Aquí podrías implementar lógica adicional para manejar errores

    def crear_widget_pedido(self, pieza_str: str, guarda_str: str, color: str):
        """Crea un widget para mostrar un pedido"""
        # Cálculos de tamaños basados en el factor de escala
        widget_height = int(60 * self.font_scale)
        tipo_size = int(13 * self.font_scale)
        medio_size = int(10 * self.font_scale)
        final_size = int(18 * self.font_scale)
        guarda_size = int(20 * self.font_scale)
        border_radius = int(5 * self.font_scale)
        margins = int(5 * self.font_scale)
        spacing = int(guarda_size * 0.15)

        widget = QFrame()
        widget.setFixedHeight(max(40, widget_height))
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: {border_radius}px;
                padding: 0px;
                margin: 0px;
            }}
        """)
        
        widget_layout = QHBoxLayout(widget)
        widget_layout.setContentsMargins(margins, 0, margins, 0)
        widget_layout.setSpacing(spacing)

        # Panel de código de pieza
        pieza_panel = self._create_pieza_panel(pieza_str, tipo_size, medio_size, final_size)
        widget_layout.addWidget(pieza_panel)

        # Panel de número de guarda (si corresponde)
        if self.show_guarda:
            guarda_panel = self._create_guarda_panel(guarda_str, guarda_size, spacing)
            widget_layout.addWidget(guarda_panel)
            widget_layout.setSpacing(spacing)
        else:
            widget_layout.setSpacing(0)

        widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        return widget, widget_layout

    def _create_pieza_panel(self, pieza_str: str, tipo_size: int, medio_size: int, final_size: int) -> QWidget:
        """Crea el panel del código de pieza"""
        pieza_panel = QWidget()
        pieza_layout = QHBoxLayout(pieza_panel)
        pieza_layout.setContentsMargins(0, 0, 0, 0)
        
        if not self.show_guarda:
            tipo_size = int(15 * self.font_scale)
            medio_size = int(12 * self.font_scale)
            final_size = int(22 * self.font_scale)
            pieza_layout.setSpacing(int(4 * self.font_scale))
        else:
            pieza_layout.setSpacing(int(2 * self.font_scale))

        # Componentes del código de pieza
        tipo = QLabel(f'<span style="font-size:{tipo_size}pt; font-weight:bold;">{pieza_str[:2]}</span>')
        tipo.setMinimumWidth(int(25 * self.font_scale))
        tipo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        medio = QLabel(f'<span style="font-size:{medio_size}pt;">{pieza_str[2:-5]}</span>')
        medio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        final = QLabel(f'<span style="font-size:{final_size}pt; font-weight:bold;">{pieza_str[-5:-2]}</span>')
        final.setMinimumWidth(int(45 * self.font_scale))
        final.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if not self.show_guarda:
            pieza_layout.addStretch(1)
        
        pieza_layout.addWidget(tipo)
        pieza_layout.addWidget(medio)
        pieza_layout.addWidget(final)
        pieza_layout.addStretch(1)

        return pieza_panel

    def _create_guarda_panel(self, guarda_str: str, guarda_size: int, spacing: int) -> QWidget:
        """Crea el panel del número de guarda"""
        guarda_container = QWidget()
        guarda_layout = QHBoxLayout(guarda_container)
        guarda_layout.setContentsMargins(0, 0, 0, 0)
        guarda_layout.setSpacing(0)
        
        guarda_label = QLabel(f'<span style="font-size:{guarda_size}pt; font-weight:bold;">{guarda_str}</span>')
        label_width = int(60 * self.font_scale)
        guarda_label.setFixedWidth(label_width)
        guarda_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        border_width = max(2, int(2 * self.font_scale))
        padding = int(4 * self.font_scale)
        
        guarda_label.setStyleSheet(f"""
            QLabel {{
                border: {border_width}px solid #000000;
                border-radius: {int(3 * self.font_scale)}px;
                background-color: rgba(255, 255, 255, 0.1);
                padding-left: {padding}px;
                padding-right: {padding}px;
            }}
        """)
        
        guarda_layout.addWidget(guarda_label)
        return guarda_container

    def _send_status_update(self, pieza: str, nuevo_estado: str) -> None:
        """Envía actualización de estado al servidor"""
        try:
            url = f"{self.server_url}pedido/{pieza}"
            requests.put(url, json={"estado": nuevo_estado}, timeout=5)
        except Exception as e:
            print(f"❌ Error al actualizar estado en servidor: {e}")
            self._show_connection_error(f"No se pudo actualizar el estado: {e}")

    def _show_connection_error(self, message: str) -> None:
        """Muestra un error de conexión al usuario"""
        QMessageBox.warning(self, "Error de Conexión", message)

    def _load_existing_orders(self) -> None:
        """Carga pedidos existentes - implementado por clases hijas"""
        try:
            self.cargar_existentes()
        except Exception as e:
            print(f"❌ Error al cargar pedidos existentes: {e}")

    def _update_ui(self) -> None:
        """Actualiza la interfaz de usuario - alias para mantener compatibilidad"""
        self.actualizar_ui_inteligentemente()

    def closeEvent(self, event):
        """Maneja el cierre de la aplicación"""
        if hasattr(self, 'ws_worker'):
            self.ws_worker.stop()
        if hasattr(self, 'ws_thread'):
            self.ws_thread.quit()
            self.ws_thread.wait()
        event.accept()

    # Métodos abstractos que deben ser implementados por las clases hijas
    def handle_nuevo_pedido(self, data: dict) -> None:
        """Maneja un nuevo pedido recibido vía WebSocket"""
        raise NotImplementedError("Las clases hijas deben implementar handle_nuevo_pedido")

    def actualizar_ui_inteligentemente(self) -> None:
        """Actualiza la interfaz de usuario de forma inteligente"""
        raise NotImplementedError("Las clases hijas deben implementar actualizar_ui_inteligentemente")

    def marcar(self, pieza: str, event) -> None:
        """Maneja el marcado de pedidos"""
        raise NotImplementedError("Las clases hijas deben implementar marcar")

    def cargar_existentes(self) -> None:
        """Carga pedidos existentes desde el servidor"""
        raise NotImplementedError("Las clases hijas deben implementar cargar_existentes")