import random
import numpy as np

# Bounding box for Temuco
TEMUCO_BOUNDS = {
    "min_lat": -38.77, "max_lat": -38.70,
    "min_lon": -72.65, "max_lon": -72.55
}

def numero_a_letras(num):
    letras = ""
    while num > 0:
        num -= 1
        letras = chr(ord('A') + (num % 26)) + letras
        num //= 26
    return letras
def generar_nodos(n):
    n_storage = int(n * 0.2)
    n_recharge = int(n * 0.2)
    n_client = n - n_storage - n_recharge
    nodos = []
    contador_letras = 1
    contador_clientes = 1

    # Generate unique coordinates for all nodes
    lats = np.random.uniform(TEMUCO_BOUNDS["min_lat"], TEMUCO_BOUNDS["max_lat"], n)
    lons = np.random.uniform(TEMUCO_BOUNDS["min_lon"], TEMUCO_BOUNDS["max_lon"], n)
    coords = list(zip(lats, lons))
    random.shuffle(coords) # Shuffle to assign randomly to different node types

    coord_idx = 0

    for _ in range(n_storage):
        lat, lon = coords[coord_idx]
        coord_idx += 1
        nodos.append({
            "id": numero_a_letras(contador_letras),
            "role": "storage",
            "lat": lat,
            "lon": lon
        })
        contador_letras += 1

    for _ in range(n_recharge):
        lat, lon = coords[coord_idx]
        coord_idx += 1
        nodos.append({
            "id": numero_a_letras(contador_letras),
            "role": "recharge",
            "lat": lat,
            "lon": lon
        })
        contador_letras += 1

    for _ in range(n_client):
        lat, lon = coords[coord_idx]
        coord_idx += 1
        tipo_cliente = random.choice(["premium", "normal"])
        nodos.append({
            "id": numero_a_letras(contador_letras),
            "role": "client",
            "client_id": f"C{contador_clientes:03d}",
            "nombre": f"Client{contador_clientes - 1}", # Corrected to match client_id
            "tipo": tipo_cliente,
            "lat": lat,
            "lon": lon
        })
        contador_letras += 1
        contador_clientes += 1

    return nodos