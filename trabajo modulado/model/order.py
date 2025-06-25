from datetime import datetime, timedelta
import random

def generar_ordenes(n_orders, nodos):
    clientes = [n for n in nodos if n["role"] == "client"]
    storages = [n for n in nodos if n["role"] == "storage"]

    if not clientes or not storages:
        return []

    ordenes = []
    for i in range(1, n_orders + 1):
        cliente = random.choice(clientes)
        destino = random.choice(storages)
        origen = cliente

        fecha_creacion = datetime.now()
        prioridad = random.randint(1, 3)

        orden = {
            "id": f"O{i}",
            "cliente": cliente["nombre"],
            "cliente_id": cliente["client_id"],
            "origen": origen["id"],
            "destino": destino["id"],
            "status": "Pendiente",
            "fecha_creacion": fecha_creacion.strftime("%Y-%m-%d %H:%M:%S"),
            "prioridad": prioridad,
            "fecha_entrega": None,
            "costo_total": 0
        }
        ordenes.append(orden)

    return ordenes

