from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from typing import List

app = FastAPI()

# CORS para permitir acceso desde cualquier cliente
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexión a la base de datos
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pieza TEXT,
            guarda TEXT,
            estado TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Modelo de pedido entrante
class Pedido(BaseModel):
    pieza: str
    guarda: str

# Lista de conexiones WebSocket
conexiones: List[WebSocket] = []

@app.post("/pedido")
async def nuevo_pedido(pedido: Pedido):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO pedidos (pieza, guarda, estado) VALUES (?, ?, ?)",
              (pedido.pieza, pedido.guarda, "nuevo"))
    conn.commit()
    conn.close()

    # Notificar a todos los clientes WebSocket conectados
    for ws in conexiones:
        await ws.send_json({
            "pieza": pedido.pieza,
            "guarda": pedido.guarda,
            "estado": "nuevo"
        })

    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    conexiones.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # No esperamos mensajes, solo mantenemos abierto
    except:
        conexiones.remove(websocket)

from fastapi.responses import JSONResponse

@app.get("/pedidos")
async def obtener_pedidos():
    try:
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT pieza, guarda FROM pedidos WHERE estado = 'nuevo'")
        rows = c.fetchall()
        conn.close()

        pedidos = [{"pieza": row[0], "guarda": row[1]} for row in rows]
        return JSONResponse(content=pedidos)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
