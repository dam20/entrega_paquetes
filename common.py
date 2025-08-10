import sys
import requests
import json
import time
import threading
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QFrame, QSizePolicy,
    QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtCore import (
    QObject, QThread, Signal, Slot, Qt
)
from websocket import WebSocketApp

# Constantes compartidas
SERVER_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"

# --- Clase del Trabajador para el WebSocket (QThread) ---
class WsWorker(QObject):
    pedido_recibido = Signal(dict)

    def __init__(self, ws_url):
        super().__init__()
        self.ws_url = ws_url
        self.ws = None

    @Slot()
    def run_forever(self):
        print("Iniciando hilo de WebSocket...")
        while True:
            try:
                self.ws = WebSocketApp(self.ws_url, on_message=self.on_message, on_close=self.on_close)
                self.ws.run_forever()
            except Exception as e:
                print(f"⚠️ WS desconectado: {e}. Reintentando en 5 segundos...")
                time.sleep(5)

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            self.pedido_recibido.emit(data)
        except Exception as e:
            print(f"❌ Error procesando mensaje WebSocket: {e}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"WS cerrado con estado {close_status_code}: {close_msg}")

class BaseApp(QMainWindow):
    def __init__(self, titulo, show_guarda=True):
        """
        Inicializa la aplicación base.
        
        Args:
            titulo (str): Título de la ventana
            show_guarda (bool): Indica si se debe mostrar el número de guarda
        """
        super().__init__()
        self.setWindowTitle(titulo)
        self.show_guarda = show_guarda  # Configura la visibilidad del número de guarda
        
        # Obtenemos la resolución de la pantalla y el espacio disponible
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        available_geometry = screen.availableGeometry()
        
        # Calculamos dimensiones considerando la barra de título (23px)
        title_bar_height = 32  # Altura típica de la barra de título en Windows
        window_width = min(230, int(screen_geometry.width() * 0.25))  # 25% del ancho o 230px
        window_height = available_geometry.height() - title_bar_height  # Altura disponible menos barra de título
        font_scale = min(1.0, screen_geometry.width() / 1024)  # Factor de escala para fuentes

        # Guardamos el factor de escala para usarlo en crear_widget_pedido
        self.font_scale = font_scale
        
        # Configuramos el widget central
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Creamos el área de desplazamiento
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(f"""
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
        """)

        # Contenedor para los widgets de pedidos
        content_widget = QWidget()
        self.layout = QVBoxLayout(content_widget)
        spacing = max(2, int(3 * font_scale))  # Reducido de 5 a 3
        self.layout.setSpacing(spacing)
        margins = max(2, int(3 * font_scale))  # Reducido de 5 a 3
        self.layout.setContentsMargins(margins, margins, margins, margins)

        # Configuramos el área de desplazamiento
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # Configuramos las flags de la ventana
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowStaysOnTopHint  # Mantener siempre visible
        )
        
        # Establecemos el tamaño de la ventana
        self.setFixedWidth(window_width)
        self.setFixedHeight(window_height)  # Altura ajustada considerando la barra de título
        
        # Posicionamos la ventana en el borde derecho
        self.move(
            available_geometry.right() - window_width,  # Pegado al borde derecho
            available_geometry.top()  # Alineado con el borde superior del área disponible
        )
        
        self.pedidos = {}
        self.widgets = {}

        self.cargar_existentes()

        self.ws_thread = QThread()
        self.ws_worker = WsWorker(WS_URL)
        self.ws_worker.moveToThread(self.ws_thread)

        self.ws_worker.pedido_recibido.connect(self.handle_nuevo_pedido)
        self.ws_thread.started.connect(self.ws_worker.run_forever)
        self.ws_thread.start()
        
        self.actualizar_ui_inteligentemente()

    def crear_widget_pedido(self, pieza_str, guarda_str, color):
        # Calculamos tamaños basados en el factor de escala
        widget_height = int(60 * self.font_scale)  # Reducido de 80 a 60
        tipo_size = int(13 * self.font_scale)
        medio_size = int(10 * self.font_scale)
        final_size = int(18 * self.font_scale)
        guarda_size = int(20 * self.font_scale)
        border_radius = int(5 * self.font_scale)
        margins = int(5 * self.font_scale)  # Reducido de 8 a 5
        # Hacemos que el espaciado sea relativo al tamaño de la fuente de guarda
        spacing = int(guarda_size * 0.15)  # Reducido de 0.25 a 0.15

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
        pieza_label_full = QWidget()
        pieza_label_full_layout = QHBoxLayout(pieza_label_full)
        pieza_label_full_layout.setContentsMargins(0, 0, 0, 0)
        
        if not self.show_guarda:
            # Aumentamos los tamaños cuando no hay número de guarda
            tipo_size = int(15 * self.font_scale)
            medio_size = int(12 * self.font_scale)
            final_size = int(22 * self.font_scale)
            pieza_label_full_layout.setSpacing(int(4 * self.font_scale))
        else:
            pieza_label_full_layout.setSpacing(int(2 * self.font_scale))

        # Tipo (2 letras)
        tipo = QLabel(f'<span style="font-size:{tipo_size}pt; font-weight:bold;">{pieza_str[:2]}</span>')
        tipo.setMinimumWidth(int(25 * self.font_scale))
        tipo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Número central
        medio = QLabel(f'<span style="font-size:{medio_size}pt;">{pieza_str[2:-5]}</span>')
        medio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Últimos 3 dígitos
        final = QLabel(f'<span style="font-size:{final_size}pt; font-weight:bold;">{pieza_str[-5:-2]}</span>')
        final.setMinimumWidth(int(45 * self.font_scale))
        final.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Agregamos un stretch al inicio y al final para centrar todo
        if not self.show_guarda:
            pieza_label_full_layout.addStretch(1)
        
        pieza_label_full_layout.addWidget(tipo)
        pieza_label_full_layout.addWidget(medio)
        pieza_label_full_layout.addWidget(final)
        pieza_label_full_layout.addStretch(1)

        # Número de guarda (con borde)
        guarda_container = QWidget()  # Contenedor sin borde
        guarda_container_layout = QHBoxLayout(guarda_container)
        guarda_container_layout.setContentsMargins(0, 0, 0, 0)
        guarda_container_layout.setSpacing(0)
        
        guarda_label = QLabel(f'<span style="font-size:{guarda_size}pt; font-weight:bold;">{guarda_str}</span>')
        # Ajustamos el ancho para números de 3 dígitos
        label_width = int(60 * self.font_scale)  # Reducido de 70 a 60
        guarda_label.setFixedWidth(label_width)
        guarda_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Aplicar el borde y fondo directamente al QLabel
        border_width = max(2, int(2 * self.font_scale))  # Reducido de 2.5 a 2
        padding = int(4 * self.font_scale)  # Reducido de 6 a 4
        guarda_label.setStyleSheet(f"""
            QLabel {{
                border: {border_width}px solid #000000;
                border-radius: {int(3 * self.font_scale)}px;
                background-color: rgba(255, 255, 255, 0.1);
                padding-left: {padding}px;
                padding-right: {padding}px;
            }}
        """)
        
        guarda_container_layout.addWidget(guarda_label)
        
        # Agregamos los widgets al layout según la configuración
        widget_layout.addWidget(pieza_label_full)
        if self.show_guarda:
            widget_layout.addWidget(guarda_container)
            widget_layout.setSpacing(spacing)  # Aplicamos el espaciado solo si hay número de guarda
        else:
            widget_layout.setSpacing(0)  # Sin espaciado cuando solo hay número de pieza

        # Configuramos el widget para que tome el tamaño mínimo necesario
        widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        return widget, widget_layout


    def _enviar_actualizacion(self, pieza, nuevo_estado):
        try:
            requests.put(f"{SERVER_URL}/pedido/{pieza}", json={"estado": nuevo_estado}, timeout=5)
        except Exception as e:
            print(f"❌ Error al actualizar estado en servidor: {e}")

    # Métodos abstractos que deben ser implementados por las clases hijas
    def handle_nuevo_pedido(self, data):
        raise NotImplementedError()

    def actualizar_ui_inteligentemente(self):
        raise NotImplementedError()

    def marcar(self, pieza, event):
        raise NotImplementedError()

    def cargar_existentes(self):
        raise NotImplementedError()
