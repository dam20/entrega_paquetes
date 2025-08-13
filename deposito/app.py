import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Slot
import threading
import requests
from common import BaseApp


class DepositoApp(BaseApp):
    """Aplicación para el sector de depósito"""
    
    def __init__(self, server_url: str, ws_url: str):
        super().__init__("Depósito", server_url, ws_url, show_guarda=True)

    @Slot(dict)
    def handle_nuevo_pedido(self, data: dict) -> None:
        """Maneja nuevos pedidos recibidos vía WebSocket"""
        pieza = data.get("pieza")
        guarda = data.get("guarda")
        estado = data.get("estado", "Pedido al Deposito")
        
        if not pieza or not guarda:
            print(f"⚠️ Datos incompletos en pedido: {data}")
            return
        
        print(f"📦 Pedido recibido - Pieza: {pieza}, Guarda: {guarda}, Estado: {estado}")

        # Actualizar si es un pedido nuevo o cambió de estado
        if pieza not in self.pedidos or self.pedidos[pieza]["estado"] != estado:
            self.pedidos[pieza] = {
                "estado": estado, 
                "datos": {"pieza": pieza, "guarda": guarda}
            }
            self.actualizar_ui_inteligentemente()

    def actualizar_ui_inteligentemente(self) -> None:
        """Actualiza la interfaz de usuario de forma eficiente"""
        # Limpiar layout existente
        self._clear_layout()

        # Filtrar pedidos visibles para depósito
        estados_visibles = ["Pedido al Deposito", "No Entregado"]
        pedidos_visibles = {
            pieza: info 
            for pieza, info in self.pedidos.items() 
            if info["estado"] in estados_visibles
        }

        # Limpiar widgets obsoletos
        self._cleanup_obsolete_widgets(pedidos_visibles)

        # Crear y agregar widgets actualizados
        self._create_and_add_widgets(pedidos_visibles)

        # Agregar stretch al final
        self.layout.addStretch()

    def _clear_layout(self) -> None:
        """Limpia el layout eliminando todos los elementos"""
        while self.layout.count() > 0:
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                self.layout.removeItem(item)

    def _cleanup_obsolete_widgets(self, pedidos_visibles: dict) -> None:
        """Elimina widgets que ya no son necesarios"""
        widgets_obsoletos = set(self.widgets.keys()) - set(pedidos_visibles.keys())
        for pieza in widgets_obsoletos:
            if pieza in self.widgets:
                del self.widgets[pieza]

    def _create_and_add_widgets(self, pedidos_visibles: dict) -> None:
        """Crea y agrega widgets para pedidos visibles, priorizando 'No Entregado' y respetando el orden de llegada"""
    
        # Orden por prioridad de estado: primero "No Entregado", luego "Pedido al Deposito"
        orden_estados = ["No Entregado", "Pedido al Deposito"]

        for estado in orden_estados:
            for pieza, info in pedidos_visibles.items():
                if info["estado"] == estado:
                    datos = info["datos"]
                    color = self._get_color_for_status(estado)

                    widget, widget_layout = self.crear_widget_pedido(
                        datos["pieza"],
                        datos["guarda"],
                        color
                    )

                    self._configure_widget_events(widget, widget_layout, pieza)
                    self.widgets[pieza] = widget
                    self.layout.addWidget(widget)

    def _get_color_for_status(self, estado: str) -> str:
        """Obtiene el color correspondiente al estado"""
        color_mapping = {
            "Pedido al Deposito": "#f1c40f",  # Amarillo
            "No Entregado": "#e74c3c"        # Rojo
        }
        return color_mapping.get(estado, "#95a5a6")  # Gris por defecto

    def _configure_widget_events(self, widget, widget_layout, pieza: str) -> None:
        """Configura los eventos de clic para el widget"""
        # Evento principal del widget
        widget.mousePressEvent = lambda event, p=pieza: self.marcar(p, event)
        
        # Eventos para elementos hijos
        for child in widget_layout.children():
            if hasattr(child, 'mousePressEvent'):
                child.mousePressEvent = lambda event, p=pieza: self.marcar(p, event)

    def marcar(self, pieza: str, event) -> None:
        """Maneja el marcado de pedidos según su estado actual"""
        if pieza not in self.pedidos:
            print(f"⚠️ Pedido {pieza} no encontrado")
            return

        estado_actual = self.pedidos[pieza]["estado"]
        nuevo_estado = self._get_next_status(estado_actual)
        
        if not nuevo_estado:
            print(f"⚠️ No hay transición disponible para estado: {estado_actual}")
            return

        # Actualizar estado y UI
        self._update_order_status(pieza, nuevo_estado)

    def _get_next_status(self, estado_actual: str) -> str:
        """Obtiene el próximo estado según el estado actual"""
        status_transitions = {
            "Pedido al Deposito": "Listo para ser Entregado",
            "No Entregado": "En Deposito"
        }
        return status_transitions.get(estado_actual)

    def _update_order_status(self, pieza: str, nuevo_estado: str) -> None:
        """Actualiza el estado del pedido local y remotamente"""
        # Actualizar estado local
        self.pedidos[pieza]["estado"] = nuevo_estado
        print(f"📦 {pieza} → {nuevo_estado}")
        
        # Actualizar UI inmediatamente
        self.actualizar_ui_inteligentemente()
        
        # Enviar actualización al servidor en segundo plano
        threading.Thread(
            target=self._send_status_update, 
            args=(pieza, nuevo_estado), 
            daemon=True
        ).start()

    def cargar_existentes(self) -> None:
        """Carga pedidos existentes desde el servidor"""
        try:
            url = f"{self.server_url}pedidos"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                pedidos_data = response.json()
                self._process_existing_orders(pedidos_data)
                print(f"✅ Cargados {len(pedidos_data)} pedidos existentes")
            else:
                print(f"⚠️ Error del servidor: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error al cargar pedidos existentes: {e}")
            self._handle_connection_error(e)

    def _process_existing_orders(self, pedidos_data: list) -> None:
        """Procesa la lista de pedidos existentes"""
        for pedido in pedidos_data:
            try:
                pieza = pedido.get("pieza")
                guarda = pedido.get("guarda")
                estado = pedido.get("estado")
                
                if pieza and guarda and estado:
                    self.pedidos[pieza] = {
                        "estado": estado,
                        "datos": {"pieza": pieza, "guarda": guarda}
                    }
                else:
                    print(f"⚠️ Pedido con datos incompletos: {pedido}")
                    
            except Exception as e:
                print(f"❌ Error procesando pedido {pedido}: {e}")

    def _handle_connection_error(self, error) -> None:
        """Maneja errores de conexión con el servidor"""
        error_message = f"No se pudo conectar con el servidor: {error}"
        print(f"❌ {error_message}")
        # Aquí podrías mostrar una notificación al usuario si es necesario


def main():
    """Función principal para ejecutar la aplicación de depósito directamente"""
    print("⚠️ Ejecute main.py para seleccionar el sector correctamente")
    sys.exit(1)


if __name__ == "__main__":
    main()