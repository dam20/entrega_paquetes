import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Slot
import threading
import requests
from common import BaseApp, SERVER_URL

class DepositoApp(BaseApp):
    def __init__(self):
        super().__init__("Depósito")

    @Slot(dict)
    def handle_nuevo_pedido(self, data):
        pieza = data["pieza"]
        guarda = data["guarda"]
        estado = data.get("estado", "Pedido al Deposito")
        
        print(f"DEBUG - Nuevo pedido recibido: Pieza={pieza}, Guarda={guarda}, Estado={estado}")  # Debug info

        if pieza not in self.pedidos or self.pedidos[pieza]["estado"] != estado:
            self.pedidos[pieza] = {"estado": estado, "datos": {"pieza": pieza, "guarda": guarda}}
            self.actualizar_ui_inteligentemente()

    def actualizar_ui_inteligentemente(self):
        # Primero, limpiar el layout existente
        while self.layout.count() > 0:
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                self.layout.removeItem(item)

        # Actualizar los widgets visibles
        visibles = {p: i for p, i in self.pedidos.items() if i["estado"] in ["Pedido al Deposito", "No Entregado"]}
        
        # Limpiar widgets que ya no son visibles
        widgets_a_eliminar = set(self.widgets.keys()) - set(visibles.keys())
        for pieza in widgets_a_eliminar:
            if pieza in self.widgets:
                del self.widgets[pieza]

        # Crear y agregar widgets en orden
        for pieza, info in visibles.items():
            estado = info["estado"]
            color = "#f1c40f" if estado == "Pedido al Deposito" else "#e74c3c"  # amarillo para Pedido, rojo para No Entregado
            datos = info["datos"]
            
            widget, widget_layout = self.crear_widget_pedido(
                datos["pieza"],
                datos["guarda"],
                color
            )

            widget.mousePressEvent = lambda event, p=pieza: self.marcar(p, event)
            for child in widget_layout.children():
                child.mousePressEvent = lambda event, p=pieza: self.marcar(p, event)

            self.widgets[pieza] = widget
            self.layout.addWidget(widget)
        
        # Agregar el stretch al final
        self.layout.addStretch()

    def marcar(self, pieza, event):
        if pieza not in self.pedidos:
            return
            
        estado_actual = self.pedidos[pieza]["estado"]
        
        # Primero actualizar el estado
        if estado_actual == "Pedido al Deposito":
            nuevo_estado = "Listo para ser Entregado"
        elif estado_actual == "No Entregado":
            nuevo_estado = "En Deposito"
        else:
            return
            
        # Luego enviar la actualización al servidor
        threading.Thread(target=self._enviar_actualizacion, args=(pieza, nuevo_estado), daemon=True).start()
        
        # Finalmente actualizar el estado local y la UI
        self.pedidos[pieza]["estado"] = nuevo_estado
        print(f"Paquete {pieza} → {nuevo_estado}")
        self.actualizar_ui_inteligentemente()

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
