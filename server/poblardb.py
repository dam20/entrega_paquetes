import sqlite3
import random

# Conexión a la base de datos
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Opcional: limpiar la tabla antes de poblarla
cursor.execute("DELETE FROM pedidos")

# Estados posibles
estados = [
    "Pedido al Deposito",
    "Listo para ser Entregado",
    "Entregado al Cliente",
    "No Entregado",
    "En Deposito"
]

# Generar 50 piezas aleatorias
def generar_pieza():
    prefix = "HC"
    middle = f"{random.randint(10000,99999)}{random.randint(1000,9999)}"
    suffix = "AR"
    return prefix + middle + suffix

def generar_guarda():
    return str(random.randint(1, 150))

# Poblar la base de datos con 50 piezas aleatorias
for _ in range(50):
    pieza = generar_pieza()
    guarda = generar_guarda()
    estado = random.choice(estados)
    cursor.execute(
        "INSERT INTO pedidos (pieza, guarda, estado) VALUES (?, ?, ?)",
        (pieza, guarda, estado)
    )

conn.commit()
conn.close()

print("✅ Se han insertado 50 piezas de prueba en la base de datos.")
