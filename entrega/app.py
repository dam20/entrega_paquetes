import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, 
    QLabel, QFrame, QSizePolicy
)
from PySide6.QtCore import Slot, Qt
import threading
import requests
from common import BaseApp, SERVER_URL

class EntregaApp(BaseApp):
    def __init__(self):
        super().__init__("Entrega", show_guarda=False)

    @Slot(dict)
    def handle_nuevo_pedido(self, data):
        pieza = data["pieza"]
        guarda = data["guarda"]
        estado = data.get("estado", "Pedido al Deposito")

        if pieza not in self.pedidos or self.pedidos[pieza]["estado"] != estado:
            self.pedidos[pieza] = {
                "estado": estado,
                "datos": {"pieza": pieza, "guarda": guarda}
            }
            self.actualizar_ui_inteligentemente()

    def actualizar_ui_inteligentemente(self):
        visibles = {p: i for p, i in self.pedidos.items() if i["estado"] == "Listo para ser Entregado"}

        widgets_a_eliminar = set(self.widgets.keys()) - set(visibles.keys())
        for pieza in widgets_a_eliminar:
            self.widgets[pieza].deleteLater()
            del self.widgets[pieza]

        for pieza, info in visibles.items():
            if pieza not in self.widgets:
                datos = info["datos"]
                
                widget, widget_layout = self.crear_widget_pedido(
                    datos["pieza"],
                    datos["guarda"],
                    "#2ecc71"
                )

                widget.mouseDoubleClickEvent = lambda event, p=pieza: self.marcar(p, event)
                widget.mousePressEvent = lambda event, p=pieza: self.marcar(p, event)
                for child in widget_layout.children():
                    child.mouseDoubleClickEvent = lambda event, p=pieza: self.marcar(p, event)
                    child.mousePressEvent = lambda event, p=pieza: self.marcar(p, event)

                self.widgets[pieza] = widget
                self.layout.addWidget(widget)
        
        # Aseguramos que haya un único stretch al final
        for i in range(self.layout.count()):
            item = self.layout.itemAt(i)
            if item is not None and item.spacerItem() is not None:
                self.layout.removeItem(item)
        self.layout.addStretch()

    def copiar_al_portapapeles(self, pieza):
        QApplication.clipboard().setText(pieza)
        print(f"📋 Número de pieza {pieza} copiado al portapapeles")

    def marcar(self, pieza, event):
        # Manejar Shift + Clic
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            nuevo_estado = "No Entregado"
            self.pedidos[pieza]["estado"] = nuevo_estado
            print(f"📦 Paquete {pieza} → {nuevo_estado}")
            self.actualizar_ui_inteligentemente()
            threading.Thread(target=self._enviar_actualizacion, args=(pieza, nuevo_estado), daemon=True).start()
            return

        # Manejar clic simple (copiar al portapapeles)
        if event.type() == event.Type.MouseButtonPress and not hasattr(event, '_double_click'):
            self.copiar_al_portapapeles(pieza)
            # Iniciar temporizador para detectar doble clic
            QApplication.instance().processEvents()
            return

        # Manejar doble clic (marcar como entregado)
        if event.type() == event.Type.MouseButtonDblClick:
            nuevo_estado = "Entregado al Cliente"
            self.pedidos[pieza]["estado"] = nuevo_estado
            print(f"📦 Paquete {pieza} → {nuevo_estado}")
            self.actualizar_ui_inteligentemente()
            threading.Thread(target=self._enviar_actualizacion, args=(pieza, nuevo_estado), daemon=True).start()

    def cargar_existentes(self):
        try:
            estados = "Listo para ser Entregado"
            r = requests.get(f"{SERVER_URL}/pedidos?estado={estados}", timeout=5)
            if r.status_code == 200:
                for p in r.json():
                    pieza = p["pieza"]
                    guarda = p["guarda"]
                    estado = p["estado"]
                    self.pedidos[pieza] = {
                        "estado": estado,
                        "datos": {"pieza": pieza, "guarda": guarda}
                    }
        except Exception as e:
            print(f"❌ Error al cargar pedidos existentes: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EntregaApp()
    window.show()
    sys.exit(app.exec())
