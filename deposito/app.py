import tkinter as tk
import threading
import json
import requests
from websocket import WebSocketApp

SERVER_URL = "http://localhost:8000"  # Cambiar si el servidor está en otra PC
WS_URL = "ws://localhost:8000/ws"

class DepositoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Depósito - Paquetes Recibidos")
        self.frame = tk.Frame(root, padx=20, pady=20)
        self.frame.pack()

        self.pedidos = {}  # id: {"frame": ..., "estado": ..., "datos": {...}}

        # Lanzar WebSocket en un hilo separado
        threading.Thread(target=self.listen_ws, daemon=True).start()

        self.refresh_ui()

    def refresh_ui(self):
        for widget in self.frame.winfo_children():
            widget.destroy()

        for idx, (pieza, info) in enumerate(self.pedidos.items()):
            estado = info["estado"]
            datos = info["datos"]

            color = {
                "nuevo": "#f1c40f",    # amarillo
                "listo": "#2ecc71",    # verde
                "devuelto": "#e74c3c"  # rojo
            }.get(estado, "#bdc3c7")  # gris default

            label_text = f"{datos['pieza'][:2]}-{datos['pieza'][-4:]} - {datos['guarda']}"

            btn = tk.Button(self.frame, text=label_text,
                            width=30, height=2, bg=color,
                            command=lambda p=pieza: self.marcar(p))
            btn.grid(row=idx, column=0, padx=5, pady=5)

        self.root.after(1000, self.refresh_ui)

    def marcar(self, pieza):
        shift_pressed = self.root.tk.call('tk::unsupported::MacWindowStyle', 'style') == 'shift' if hasattr(tk, 'call') else False
        estado_actual = self.pedidos[pieza]["estado"]

        if estado_actual == "nuevo":
            nuevo_estado = "devuelto" if shift_pressed else "listo"
        elif estado_actual in ["listo", "devuelto"]:
            return

        self.pedidos[pieza]["estado"] = nuevo_estado
        print(f"Paquete {pieza} → {nuevo_estado.upper()}")

    def listen_ws(self):
        def on_message(ws, message):
            data = json.loads(message)
            pieza = data["pieza"]
            guarda = data["guarda"]

            if pieza not in self.pedidos:
                self.pedidos[pieza] = {
                    "estado": "nuevo",
                    "datos": {"pieza": pieza, "guarda": guarda}
                }

        ws = WebSocketApp(WS_URL, on_message=on_message)
        ws.run_forever()

# Lanzar app
if __name__ == "__main__":
    root = tk.Tk()
    app = DepositoApp(root)
    root.mainloop()
