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
        # Recuperamos los pedidos existentes
        self.cargar_existentes()  

        self.refresh_ui()

    def refresh_ui(self):
        for widget in self.frame.winfo_children():
            widget.destroy()

        for idx, (pieza, info) in enumerate(self.pedidos.items()):
            estado = info["estado"]
            datos = info["datos"]

            # Mostrar solo estados 'nuevo' y 'devuelto'
            if estado not in ["nuevo", "devuelto"]:
                continue

            color = {
                "nuevo": "#f1c40f",    # amarillo
                "devuelto": "#e74c3c"  # rojo
            }.get(estado, "#bdc3c7")  # gris default

            pieza_str = datos["pieza"]
            guarda_str = datos["guarda"]

            # Procesar partes de la pieza
            prefix = pieza_str[:2]             # HC
            middle = pieza_str[2:-5]           # los del medio (entre HC y los 3 finales)
            last_digits = pieza_str[-5:-2]     # los 3 últimos antes de 'AR'

            # Crear el frame para el botón custom
            btn_frame = tk.Frame(self.frame, bg=color, padx=10, pady=10)
            btn_frame.grid(row=idx, column=0, padx=5, pady=5, sticky="w")

            # Label compuesto para la pieza
            pieza_label = tk.Frame(btn_frame, bg=color)
            pieza_label.pack(side="left")

            tk.Label(pieza_label, text=prefix, font=("Arial", 14, "bold"), bg=color).pack(side="left")
            tk.Label(pieza_label, text=middle, font=("Arial", 10), bg=color).pack(side="left")
            tk.Label(pieza_label, text=last_digits, font=("Arial", 20, "bold"), bg=color).pack(side="left")

            # Espacio entre pieza y guarda
            tk.Label(btn_frame, text=" ", bg=color, width=2).pack(side="left")

            # Label para guarda
            tk.Label(btn_frame, text=guarda_str, font=("Arial", 24, "bold"), bg=color).pack(side="left")

            # Evento de clic
            btn_frame.bind("<Button-1>", lambda e, p=pieza: self.marcar(p))
            for child in btn_frame.winfo_children():
                child.bind("<Button-1>", lambda e, p=pieza: self.marcar(p))

    def marcar(self, pieza):
        shift_pressed = self.root.tk.call('tk::unsupported::MacWindowStyle', 'style') == 'shift' if hasattr(tk, 'call') else False
        estado_actual = self.pedidos[pieza]["estado"]

        if estado_actual == "nuevo":
            nuevo_estado = "devuelto" if shift_pressed else "listo"
        elif estado_actual in ["listo", "devuelto"]:
            return

        self.pedidos[pieza]["estado"] = nuevo_estado
        print(f"Paquete {pieza} → {nuevo_estado.upper()}")

    def marcar(self, pieza):
        estado_actual = self.pedidos[pieza]["estado"]
        shift_pressed = self.root.tk.call('tk::unsupported::MacWindowStyle', 'style') == 'shift' if hasattr(tk, 'call') else False

        if estado_actual == "nuevo":
            nuevo_estado = "devuelto" if shift_pressed else "listo"
        elif estado_actual in ["listo", "devuelto"]:
            return

        self.pedidos[pieza]["estado"] = nuevo_estado
        print(f"Paquete {pieza} → {nuevo_estado.upper()}")

        # Actualizar en el servidor
        try:
            requests.put(f"{SERVER_URL}/pedido/{pieza}", json={"estado": nuevo_estado}, timeout=3)
        except Exception as e:
            print(f"❌ Error al actualizar estado en el servidor: {e}")


    def listen_ws(self):
        def on_message(ws, message):
            data = json.loads(message)
            pieza = data["pieza"]
            guarda = data["guarda"]

            # Agregar o actualizar pieza
            if pieza not in self.pedidos:
                self.pedidos[pieza] = {
                    "estado": estado,
                    "datos": {"pieza": pieza, "guarda": guarda}
                }
            else:
                self.pedidos[pieza]["estado"] = estado  # actualizar estado si ya existe


        ws = WebSocketApp(WS_URL, on_message=on_message)
        ws.run_forever()
    
    def cargar_existentes(self):
        try:
            r = requests.get(f"{SERVER_URL}/pedidos", timeout=5)
            if r.status_code == 200:
                paquetes = r.json()
                for p in paquetes:
                    pieza = p["pieza"]
                    guarda = p["guarda"]
                    if pieza not in self.pedidos:
                        self.pedidos[pieza] = {
                            "estado": "nuevo",
                            "datos": {"pieza": pieza, "guarda": guarda}
                        }
        except Exception as e:
            print(f"❌ Error al cargar pedidos existentes: {e}")

# Lanzar app
if __name__ == "__main__":
    root = tk.Tk()
    app = DepositoApp(root)
    root.mainloop()
