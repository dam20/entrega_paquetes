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
    def __init__(self, titulo):
        super().__init__()
        self.setWindowTitle(titulo)
        
        # Obtenemos la resolución de la pantalla
        screen = QApplication.primaryScreen().geometry()
        screen_width = screen.width()
        screen_height = screen.height()

        # Calculamos dimensiones basadas en la resolución
        window_width = min(280, int(screen_width * 0.35))  # 35% del ancho o 280px, lo que sea menor
        window_height = min(int(screen_height * 0.9), screen_height - 50)  # 90% del alto o altura-50px
        font_scale = min(1.0, screen_width / 1024)  # Factor de escala para fuentes

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
        spacing = max(2, int(5 * font_scale))
        self.layout.setSpacing(spacing)
        margins = max(3, int(5 * font_scale))
        self.layout.setContentsMargins(margins, margins, margins, margins)
        self.layout.addStretch()

        # Configuramos el área de desplazamiento
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # Deshabilitamos la maximización y ajustamos el tamaño
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )
        
        # Establecemos el tamaño de la ventana
        self.setFixedWidth(window_width)
        self.setFixedHeight(window_height)
        
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
        widget_height = int(60 * self.font_scale)
        tipo_size = int(13 * self.font_scale)
        medio_size = int(10 * self.font_scale)
        final_size = int(18 * self.font_scale)
        guarda_size = int(20 * self.font_scale)
        border_radius = int(5 * self.font_scale)
        margins = int(8 * self.font_scale)
        spacing = int(10 * self.font_scale)

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

        # Panel izquierdo (código de pieza)
        pieza_label_full = QWidget()
        pieza_label_full_layout = QHBoxLayout(pieza_label_full)
        pieza_label_full_layout.setContentsMargins(0, 0, 0, 0)
        pieza_label_full_layout.setSpacing(int(2 * self.font_scale))

        # Tipo (2 letras)
        tipo = QLabel(f'<span style="font-size:{tipo_size}pt; font-weight:bold;">{pieza_str[:2]}</span>')
        tipo.setMinimumWidth(int(25 * self.font_scale))
        
        # Número central
        medio = QLabel(f'<span style="font-size:{medio_size}pt;">{pieza_str[2:-5]}</span>')
        
        # Últimos 3 dígitos
        final = QLabel(f'<span style="font-size:{final_size}pt; font-weight:bold;">{pieza_str[-5:-2]}</span>')
        final.setMinimumWidth(int(45 * self.font_scale))

        pieza_label_full_layout.addWidget(tipo)
        pieza_label_full_layout.addWidget(medio)
        pieza_label_full_layout.addWidget(final)
        pieza_label_full_layout.addStretch(1)

        # Número de guarda
        guarda_label = QLabel(f'<span style="font-size:{guarda_size}pt; font-weight:bold;">{guarda_str}</span>')
        guarda_label.setFixedWidth(int(50 * self.font_scale))
        guarda_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # Agregamos los widgets al layout
        widget_layout.addWidget(pieza_label_full)
        widget_layout.addWidget(guarda_label)

        # Configuramos el widget para que tome el tamaño mínimo necesario
        widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        return widget, widget_layout

        return widget, widget_layout

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
