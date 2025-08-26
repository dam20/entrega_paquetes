import base64
from fastapi import FastAPI, Request, HTTPException, WebSocket, Query 
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import sqlite3
import logging
import uvicorn
import cv2
import numpy as np

# Importa la función de procesamiento de OCR desde tu archivo externo
# Asegúrate de que extraer_datos_ocr esté definida en procesarImagen.py
from procesarImagen import extraer_datos_ocr 

# Configuración de logging para el servidor
logging.basicConfig(
    filename='server_ocr.log',
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = FastAPI()

# Middleware CORS (ya lo tenías, pero es importante reiterarlo para la claridad)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todas las origenes. En producción, especifica tus dominios.
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos los encabezados
)

# Modelos de Pydantic
class OcrRequest(BaseModel):
    imagen_pieza: str
    imagen_guarda: str

class Pedido(BaseModel):
    pieza: str
    guarda: str
    poste_restante: bool

class EstadoUpdate(BaseModel):
    estado: str

# Estados válidos para los pedidos (mover esto a un archivo de constantes si crece mucho)
ESTADOS_VALIDOS = [
    "Pedido al Deposito",
    "Listo para ser Entregado",
    "Entregado al Cliente",
    "No Entregado",
    "En Deposito"
]

# Base de datos SQLite (solo se inicializa una vez)
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pieza TEXT,
            guarda TEXT,
            estado TEXT,
            poste_restante BOOLEAN
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Lista para conexiones WebSocket (Mantener aquí si es un único archivo de servidor)
conexiones: List[WebSocket] = [] # Se necesita importar WebSocket de FastAPI

# Endpoint para verificar el estado de salud del servidor
@app.get("/health")
async def health_check():
    """Endpoint para verificar el estado de salud del servidor."""
    logging.info("Solicitud de health check recibida.")
    return {"status": "ok", "message": "Servidor de OCR funcionando correctamente."}

# Endpoint para recibir nuevos pedidos
@app.post("/pedido")
async def nuevo_pedido(pedido: Pedido):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO pedidos (pieza, guarda, estado, poste_restante) VALUES (?, ?, ?, ?)",
              (pedido.pieza, pedido.guarda, "Pedido al Deposito", pedido.poste_restante))
    conn.commit()
    conn.close()

    # Enviar actualización a los clientes WebSocket
    for ws in conexiones:
        try:
            await ws.send_json({
                "pieza": pedido.pieza,
                "guarda": pedido.guarda,
                "estado": "Pedido al Deposito"
            })
        except RuntimeError: # Manejar conexiones WebSocket cerradas
            logging.warning("No se pudo enviar mensaje a WebSocket, la conexión podría estar cerrada.")


    logging.info(f"Pedido recibido: Pieza={pedido.pieza}, Guarda={pedido.guarda}, Poste Restante={pedido.poste_restante}")
    print(f"✅ Pedido recibido en el servidor: Pieza={pedido.pieza}, Guarda={pedido.guarda}, Poste Restante={pedido.poste_restante}")
    return {"status": "ok", "message": "Pedido creado correctamente"}

# Endpoint principal para el procesamiento de OCR
@app.post("/procesarocr")
async def procesar_ocr_endpoint(request_data: OcrRequest):
    """
    Recibe imágenes codificadas en Base64, realiza OCR y devuelve el texto.
    La decodificación de Base64 y la conversión a imagen se realiza aquí.
    El OCR real se delega a una función externa.
    """
    logging.info("Solicitud de procesamiento OCR recibida.")
    try:
        # Decodificar Base64 a bytes
        bytes_pieza = base64.b64decode(request_data.imagen_pieza)
        bytes_guarda = base64.b64decode(request_data.imagen_guarda)

        # Convertir bytes a imagen OpenCV (numpy array)
        # Se usa IMREAD_UNCHANGED para mantener el canal alfa si lo hubiera,
        # aunque para b/n, IMREAD_COLOR o IMREAD_GRAYSCALE también funcionarían.
        img_pieza = cv2.imdecode(np.frombuffer(bytes_pieza, np.uint8), cv2.IMREAD_UNCHANGED)
        img_guarda = cv2.imdecode(np.frombuffer(bytes_guarda, np.uint8), cv2.IMREAD_UNCHANGED)

        if img_pieza is None or img_guarda is None:
            logging.warning("No se pudo decodificar una o ambas imágenes Base64.")
            raise HTTPException(status_code=400, detail="Imágenes Base64 inválidas o corruptas.")

        logging.info("Imágenes decodificadas correctamente. Iniciando OCR externo.")

        # Llama a la función externa para realizar el OCR
        # Asegúrate de que 'extraer_datos_ocr' en 'procesarImagen.py'
        # reciba los objetos de imagen de OpenCV (numpy arrays)
        texto_pieza, texto_guarda, poste_restante = extraer_datos_ocr(img_pieza, img_guarda)
        
        logging.info(f"OCR completado. Pieza: '{texto_pieza}', Guarda: '{texto_guarda}', Poste Restante: '{poste_restante}'")
        return {"pieza": texto_pieza, "guarda": texto_guarda, "poste_restante": poste_restante}

    except HTTPException as http_exc:
        # Re-lanzar excepciones HTTP para que FastAPI las maneje
        raise http_exc
    except Exception as e:
        logging.error(f"Error interno en /procesarocr: {e}", exc_info=True)
        # Devuelve un 500 para errores del servidor
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al procesar OCR: {e}")

# Endpoint para actualizar el estado de un pedido
@app.put("/pedido/{pieza}")
async def actualizar_estado(pieza: str, estado_update: EstadoUpdate):
    nuevo_estado = estado_update.estado
    if nuevo_estado not in ESTADOS_VALIDOS:
        raise HTTPException(status_code=400, detail="Estado inválido") # Usar HTTPException para errores FastAPI

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE pedidos SET estado = ? WHERE pieza = ?", (nuevo_estado, pieza))
    conn.commit()

    c.execute("SELECT guarda FROM pedidos WHERE pieza = ?", (pieza,))
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Pieza no encontrada") # Usar HTTPException para 404

    guarda = row[0]
    # Enviar actualización a los clientes WebSocket
    for ws in conexiones:
        try:
            await ws.send_json({
                "pieza": pieza,
                "guarda": guarda,
                "estado": nuevo_estado
            })
        except RuntimeError: # Manejar conexiones WebSocket cerradas
            logging.warning("No se pudo enviar mensaje a WebSocket, la conexión podría estar cerrada.")

    logging.info(f"Estado de pedido actualizado: Pieza={pieza}, Nuevo Estado={nuevo_estado}")
    return {"status": "ok", "pieza": pieza, "nuevo_estado": nuevo_estado}

# Endpoint para obtener pedidos
@app.get("/pedidos")
async def obtener_pedidos(estado: str = Query(default=None)):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if estado:
        estados = [e.strip() for e in estado.split(",")]
        placeholders = ",".join("?" * len(estados))
        # Asegúrate de que la consulta SQL sea segura contra inyección (FastAPI ayuda con esto en Path y Query)
        c.execute(
            f"SELECT pieza, guarda, estado FROM pedidos WHERE estado IN ({placeholders})",
            estados
        )
    else:
        c.execute("SELECT pieza, guarda, estado FROM pedidos")
    rows = c.fetchall()
    conn.close()
    return [{"pieza": r[0], "guarda": r[1], "estado": r[2]} for r in rows]

# Endpoint WebSocket
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    conexiones.append(websocket)
    logging.info(f"Nueva conexión WebSocket: {websocket.client}")
    try:
        while True:
            # Aquí puedes manejar mensajes entrantes de WebSocket si los necesitas
            # await websocket.receive_text() 
            # Si no esperas mensajes del cliente, puedes simplemente mantener la conexión viva
            await websocket.receive_text() # Opcional: para mantener la conexión
    except Exception as e:
        logging.info(f"Conexión WebSocket cerrada o error: {websocket.client} - {e}")
        conexiones.remove(websocket)
    finally:
        if websocket in conexiones: # Asegurarse de que se remueva si aún está
            conexiones.remove(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

