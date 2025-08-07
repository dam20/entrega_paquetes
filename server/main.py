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

class EstadoUpdate(BaseModel):
    estado: str


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


@app.put("/pedido/{pieza}")
async def actualizar_estado(pieza: str, estado_update: EstadoUpdate):
    nuevo_estado = estado_update.estado.lower()
    if nuevo_estado not in ["listo", "devuelto"]:
        return JSONResponse(status_code=400, content={"error": "Estado inválido"})

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE pedidos SET estado = ? WHERE pieza = ?", (nuevo_estado, pieza))
    conn.commit()

    # Obtener la guarda para enviar por WebSocket
    c.execute("SELECT guarda FROM pedidos WHERE pieza = ?", (pieza,))
    row = c.fetchone()
    conn.close()

    if not row:
        return JSONResponse(status_code=404, content={"error": "Pieza no encontrada"})

    guarda = row[0]

    # Notificar a todos los clientes WebSocket conectados
    for ws in conexiones:
        try:
            await ws.send_json({
                "pieza": pieza,
                "guarda": guarda,
                "estado": nuevo_estado
            })
        except:
            # Si falla, eliminamos la conexión muerta
            conexiones.remove(ws)

    return {"status": "ok", "pieza": pieza, "nuevo_estado": nuevo_estado}
