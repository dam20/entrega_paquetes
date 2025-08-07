from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import sqlite3

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estados
ESTADOS_VALIDOS = [
    "Pedido al Deposito",
    "Listo para ser Entregado",
    "Entregado al Cliente",
    "No Entregado",
    "En Deposito"
]

# Base de datos
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

# Modelos
class Pedido(BaseModel):
    pieza: str
    guarda: str

class EstadoUpdate(BaseModel):
    estado: str

conexiones: List[WebSocket] = []

@app.post("/pedido")
async def nuevo_pedido(pedido: Pedido):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO pedidos (pieza, guarda, estado) VALUES (?, ?, ?)",
              (pedido.pieza, pedido.guarda, "Pedido al Deposito"))
    conn.commit()
    conn.close()

    for ws in conexiones:
        await ws.send_json({
            "pieza": pedido.pieza,
            "guarda": pedido.guarda,
            "estado": "Pedido al Deposito"
        })

    return {"status": "ok"}

@app.put("/pedido/{pieza}")
async def actualizar_estado(pieza: str, estado_update: EstadoUpdate):
    nuevo_estado = estado_update.estado
    if nuevo_estado not in ESTADOS_VALIDOS:
        return JSONResponse(status_code=400, content={"error": "Estado inválido"})

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE pedidos SET estado = ? WHERE pieza = ?", (nuevo_estado, pieza))
    conn.commit()

    c.execute("SELECT guarda FROM pedidos WHERE pieza = ?", (pieza,))
    row = c.fetchone()
    conn.close()

    if not row:
        return JSONResponse(status_code=404, content={"error": "Pieza no encontrada"})

    guarda = row[0]
    for ws in conexiones:
        try:
            await ws.send_json({
                "pieza": pieza,
                "guarda": guarda,
                "estado": nuevo_estado
            })
        except:
            conexiones.remove(ws)

    return {"status": "ok", "pieza": pieza, "nuevo_estado": nuevo_estado}

@app.get("/pedidos")
async def obtener_pedidos(estado: str = Query(default=None)):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if estado:
        estados = [e.strip() for e in estado.split(",")]
        placeholders = ",".join("?" * len(estados))
        c.execute(
            f"SELECT pieza, guarda, estado FROM pedidos WHERE estado IN ({placeholders})",
            estados
        )
    else:
        c.execute("SELECT pieza, guarda, estado FROM pedidos")
    rows = c.fetchall()
    conn.close()
    return [{"pieza": r[0], "guarda": r[1], "estado": r[2]} for r in rows]

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    conexiones.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        conexiones.remove(websocket)
