import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import pyqtSlot, Qt
import threading
import requests
from common import BaseApp


class EntregaApp(BaseApp):
    """Aplicación para el sector de entrega"""
    
    def __init__(self, server_url: str, ws_url: str):
        super().__init__("Entrega", server_url, ws_url, show_guarda=False)

    @pyqtSlot(dict)
    def handle_nuevo_pedido(self, data: dict) -> None:
        """Maneja nuevos pedidos recibidos vía WebSocket"""
        pieza = data.get("pieza")
        guarda = data.get("guarda")
        estado = data.get("estado", "Pedido al Deposito")
        
        if not pieza or not guarda:
            print(f"⚠️ Datos incompletos en pedido: {data}")
            return

        print(f"🚚 Pedido recibido - Pieza: {pieza}, Estado: {estado}")

        # Actualizar si es un pedido nuevo o cambió de estado
        if pieza not in self.pedidos or self.pedidos[pieza]["estado"] != estado:
            self.pedidos[pieza] = {
                "estado": estado,
                "datos": {"pieza": pieza, "guarda": guarda}
            }
            self.actualizar_ui_inteligentemente()

    def actualizar_ui_inteligentemente(self) -> None:
        """Actualiza la interfaz de usuario de forma eficiente"""
        # Filtrar solo pedidos listos para entrega
        estados_visibles = ["Listo para ser Entregado"]
        pedidos_visibles = {
            pieza: info 
            for pieza, info in self.pedidos.items() 
            if info["estado"] in estados_visibles
        }

        # Limpiar widgets obsoletos
        self._cleanup_obsolete_widgets(pedidos_visibles)

        # Crear widgets para pedidos nuevos
        self._create_missing_widgets(pedidos_visibles)

        # Reorganizar widgets en el layout
        self._reorganize_layout(pedidos_visibles)

    def _cleanup_obsolete_widgets(self, pedidos_visibles: dict) -> None:
        """Elimina widgets que ya no son necesarios"""
        widgets_obsoletos = set(self.widgets.keys()) - set(pedidos_visibles.keys())
        for pieza in widgets_obsoletos:
            if pieza in self.widgets:
                widget = self.widgets[pieza]
                widget.deleteLater()
                del self.widgets[pieza]

    def _create_missing_widgets(self, pedidos_visibles: dict) -> None:
        """Crea widgets para pedidos que no tienen widget asociado"""
        for pieza, info in pedidos_visibles.items():
            if pieza not in self.widgets:
                self._create_widget_for_order(pieza, info)

    def _create_widget_for_order(self, pieza: str, info: dict) -> None:
        """Crea un widget para un pedido específico"""
        datos = info["datos"]
        
        widget, widget_layout = self.crear_widget_pedido(
            datos["pieza"],
            datos["guarda"],
            "#2ecc71"  # Verde para pedidos listos
        )

        # Configurar eventos
        self._configure_widget_events(widget, widget_layout, pieza)
        
        # Guardar widget
        self.widgets[pieza] = widget

    def _configure_widget_events(self, widget, widget_layout, pieza: str) -> None:
        """Configura los eventos de interacción del widget"""
        # Evento principal del widget
        widget.mouseDoubleClickEvent = lambda event, p=pieza: self.marcar(p, event)
        widget.mousePressEvent = lambda event, p=pieza: self.marcar(p, event)
        
        # Eventos para elementos hijos
        for child in widget_layout.children():
            if hasattr(child, 'mouseDoubleClickEvent'):
                child.mouseDoubleClickEvent = lambda event, p=pieza: self.marcar(p, event)
            if hasattr(child, 'mousePressEvent'):
                child.mousePressEvent = lambda event, p=pieza: self.marcar(p, event)

    def _reorganize_layout(self, pedidos_visibles: dict) -> None:
        """Reorganiza los widgets en el layout respetando el orden de llegada"""
        # Remover todos los items del layout
        while self.layout.count() > 0:
            item = self.layout.takeAt(0)
            if item.spacerItem():
                self.layout.removeItem(item)

        # Agregar widgets en el orden original de llegada
        for pieza in pedidos_visibles:
            if pieza in self.widgets:
                self.layout.addWidget(self.widgets[pieza])

        # Agregar stretch al final
        self.layout.addStretch()

    def marcar(self, pieza: str, event) -> None:
        """Maneja las diferentes acciones según el tipo de clic"""
        if pieza not in self.pedidos:
            print(f"⚠️ Pedido {pieza} no encontrado")
            return

        # Manejar Shift + Clic para marcar como "No Entregado"
        if self._is_shift_click(event):
            self._mark_as_not_delivered(pieza)
            return

        # Manejar clic simple para copiar al portapapeles
        if self._is_single_click(event):
            self._copy_to_clipboard(pieza)
            return

        # Manejar doble clic para marcar como entregado
        if self._is_double_click(event):
            self._mark_as_delivered(pieza)

    def _is_shift_click(self, event) -> bool:
        """Verifica si es un clic con Shift presionado"""
        return event.modifiers() & Qt.KeyboardModifier.ShiftModifier

    def _is_single_click(self, event) -> bool:
        """Verifica si es un clic simple"""
        return (event.type() == event.Type.MouseButtonPress and 
                not hasattr(event, '_double_click'))

    def _is_double_click(self, event) -> bool:
        """Verifica si es un doble clic"""
        return event.type() == event.Type.MouseButtonDblClick

    def _mark_as_not_delivered(self, pieza: str) -> None:
        """Marca el pedido como no entregado"""
        nuevo_estado = "No Entregado"
        self._update_order_status(pieza, nuevo_estado)
        print(f"↩️ {pieza} → {nuevo_estado}")

    def _copy_to_clipboard(self, pieza: str) -> None:
        """Copia el número de pieza al portapapeles"""
        QApplication.clipboard().setText(pieza)
        print(f"📋 Número de pieza {pieza} copiado al portapapeles")

    def _mark_as_delivered(self, pieza: str) -> None:
        """Marca el pedido como entregado al cliente"""
        nuevo_estado = "Entregado al Cliente"
        self._update_order_status(pieza, nuevo_estado)
        print(f"✅ {pieza} → {nuevo_estado}")

    def _update_order_status(self, pieza: str, nuevo_estado: str) -> None:
        """Actualiza el estado del pedido local y remotamente"""
        # Actualizar estado local
        self.pedidos[pieza]["estado"] = nuevo_estado
        
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
            # Solo cargar pedidos listos para entrega
            estados = "Listo para ser Entregado"
            url = f"{self.server_url}pedidos?estado={estados}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                pedidos_data = response.json()
                self._process_existing_orders(pedidos_data)
                print(f"✅ Cargados {len(pedidos_data)} pedidos para entrega")
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