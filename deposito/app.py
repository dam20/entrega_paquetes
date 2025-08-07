import sys
import requests
import json
import time
import threading
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QFrame
)
from PySide6.QtCore import (
    QObject, QThread, Signal, Slot, Qt
)
from websocket import WebSocketApp

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

# --- Clase Principal de la Aplicación (UI) ---
class DepositoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Depósito - Paquetes Recibidos")
        self.setGeometry(100, 100, 500, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(10, 10, 10, 10)

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

    @Slot(dict)
    def handle_nuevo_pedido(self, data):
        pieza = data["pieza"]
        guarda = data["guarda"]
        estado = data.get("estado", "Pedido al Deposito")

        if pieza not in self.pedidos or self.pedidos[pieza]["estado"] != estado:
            self.pedidos[pieza] = {"estado": estado, "datos": {"pieza": pieza, "guarda": guarda}}
            self.actualizar_ui_inteligentemente()

    def actualizar_ui_inteligentemente(self):
        visibles = {p: i for p, i in self.pedidos.items() if i["estado"] in ["Pedido al Deposito", "No Entregado"]}
        
        widgets_a_eliminar = set(self.widgets.keys()) - set(visibles.keys())
        for pieza in widgets_a_eliminar:
            self.widgets[pieza].deleteLater()
            del self.widgets[pieza]

        for pieza, info in visibles.items():
            if pieza not in self.widgets:
                estado = info["estado"]
                color = "#f1c40f" if estado == "Pedido al Deposito" else "#e74c3c"
                datos = info["datos"]
                pieza_str = datos["pieza"]
                guarda_str = datos["guarda"]
                
                widget = QFrame()
                widget.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
                widget_layout = QHBoxLayout(widget)

                pieza_label_full = QWidget()
                pieza_label_full_layout = QHBoxLayout(pieza_label_full)
                pieza_label_full_layout.setContentsMargins(0, 0, 0, 0)
                pieza_label_full_layout.addWidget(QLabel(f'<span style="font-size:14pt; font-weight:bold;">{pieza_str[:2]}</span>'))
                pieza_label_full_layout.addWidget(QLabel(f'<span style="font-size:10pt;">{pieza_str[2:-5]}</span>'))
                pieza_label_full_layout.addWidget(QLabel(f'<span style="font-size:20pt; font-weight:bold;">{pieza_str[-5:-2]}</span>'))
                
                guarda_label = QLabel(f'<span style="font-size:24pt; font-weight:bold;">{guarda_str}</span>')
                
                widget_layout.addWidget(pieza_label_full)
                widget_layout.addStretch()
                widget_layout.addWidget(guarda_label)

                widget.mousePressEvent = lambda event, p=pieza: self.marcar(p, event)
                for child in widget_layout.children():
                    child.mousePressEvent = lambda event, p=pieza: self.marcar(p, event)

                self.widgets[pieza] = widget
                self.layout.addWidget(widget)

    def marcar(self, pieza, event):
        estado_actual = self.pedidos[pieza]["estado"]

        if estado_actual == "Pedido al Deposito":
            nuevo_estado = "Listo para ser Entregado"
        elif estado_actual == "No Entregado":
            nuevo_estado = "En Deposito"
        else:
            return

        self.pedidos[pieza]["estado"] = nuevo_estado
        print(f"Paquete {pieza} → {nuevo_estado}")
        self.actualizar_ui_inteligentemente()

        threading.Thread(target=self._enviar_actualizacion, args=(pieza, nuevo_estado), daemon=True).start()

    def _enviar_actualizacion(self, pieza, nuevo_estado):
        try:
            requests.put(f"{SERVER_URL}/pedido/{pieza}", json={"estado": nuevo_estado}, timeout=5)
        except Exception as e:
            print(f"❌ Error al actualizar estado en el servidor: {e}")

    def cargar_existentes(self):
        try:
            r = requests.get(f"{SERVER_URL}/pedidos", timeout=5)
            if r.status_code == 200:
                for p in r.json():
                    pieza = p["pieza"]
                    guarda = p["guarda"]
                    estado = p["estado"]
                    self.pedidos[pieza] = {"estado": estado, "datos": {"pieza": pieza, "guarda": guarda}}
        except Exception as e:
            print(f"❌ Error al cargar pedidos existentes: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DepositoApp()
    window.show()
    sys.exit(app.exec())