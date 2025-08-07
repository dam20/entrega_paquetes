import tkinter as tk
import threading
import json
import requests
import time
from websocket import WebSocketApp
import queue

SERVER_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"

class EntregaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Entrega - Paquetes Pendientes")
        self.frame = tk.Frame(root, padx=20, pady=20)
        self.frame.pack()
        self.pedidos = {}
        self.widgets = {}
        self.cola_mensajes = queue.Queue()

        self.cargar_existentes()
        self.actualizar_ui_inteligentemente()

        threading.Thread(target=self.listen_ws, daemon=True).start()
        self.root.after(100, self.process_messages)

    def process_messages(self):
        cambios = False
        while not self.cola_mensajes.empty():
            data = self.cola_mensajes.get()
            pieza = data["pieza"]
            guarda = data["guarda"]
            estado = data.get("estado", "Pedido al Deposito")

            if pieza not in self.pedidos or self.pedidos[pieza]["estado"] != estado:
                 self.pedidos[pieza] = {
                    "estado": estado,
                    "datos": {"pieza": pieza, "guarda": guarda}
                }
                 cambios = True

        if cambios:
            self.actualizar_ui_inteligentemente()

        self.root.after(100, self.process_messages)

    def actualizar_ui_inteligentemente(self):
        visibles = {p: i for p, i in self.pedidos.items() if i["estado"] == "Listo para ser Entregado"}

        widgets_a_eliminar = set(self.widgets.keys()) - set(visibles.keys())
        for pieza in widgets_a_eliminar:
            self.widgets[pieza].destroy()
            del self.widgets[pieza]

        row = 0
        for pieza, info in visibles.items():
            btn_frame = self.widgets.get(pieza)

            if not btn_frame:
                datos = info["datos"]
                pieza_str = datos["pieza"]
                guarda_str = datos["guarda"]
                
                btn_frame = tk.Frame(self.frame, bg="#2ecc71", padx=10, pady=10)
                self.widgets[pieza] = btn_frame

                pieza_label = tk.Frame(btn_frame, bg="#2ecc71")
                pieza_label.pack(side="left")
                tk.Label(pieza_label, text=pieza_str[:2], font=("Arial", 14, "bold"), bg="#2ecc71").pack(side="left")
                tk.Label(pieza_label, text=pieza_str[2:-5], font=("Arial", 10), bg="#2ecc71").pack(side="left")
                tk.Label(pieza_label, text=pieza_str[-5:-2], font=("Arial", 20, "bold"), bg="#2ecc71").pack(side="left")

                tk.Label(btn_frame, text=" ", bg="#2ecc71", width=2).pack(side="left")
                tk.Label(btn_frame, text=guarda_str, font=("Arial", 24, "bold"), bg="#2ecc71", width=3).pack(side="left")

                self.bind_click(btn_frame, pieza)
                for child in btn_frame.winfo_children():
                    self.bind_click(child, pieza)
            
            btn_frame.grid(row=row, column=0, padx=5, pady=5, sticky="w")
            row += 1

    def bind_click(self, widget, pieza):
        widget.bind("<Button-1>", lambda e: self.marcar(pieza, e))

    def marcar(self, pieza, event):
        shift = event.state & 0x0001 != 0
        nuevo_estado = "No Entregado" if shift else "Entregado al Cliente"

        self.pedidos[pieza]["estado"] = nuevo_estado
        print(f"📦 Paquete {pieza} → {nuevo_estado}")
        self.actualizar_ui_inteligentemente()

        def enviar():
            try:
                requests.put(f"{SERVER_URL}/pedido/{pieza}", json={"estado": nuevo_estado}, timeout=5)
            except Exception as e:
                print(f"❌ Error al actualizar estado en servidor: {e}")

        threading.Thread(target=enviar, daemon=True).start()

    def listen_ws(self):
        def on_message(ws, message):
            try:
                data = json.loads(message)
                self.cola_mensajes.put(data)
            except Exception as e:
                print(f"❌ Error procesando mensaje WebSocket: {e}")

        while True:
            try:
                ws = WebSocketApp(WS_URL, on_message=on_message)
                ws.run_forever()
            except Exception as e:
                print(f"⚠️ WS desconectado: {e}")
                time.sleep(5)

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
    root = tk.Tk()
    app = EntregaApp(root)
    root.mainloop()