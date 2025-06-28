import random

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

    for _ in range(n_storage):
        nodos.append({
            "id": numero_a_letras(contador_letras),
            "role": "storage"
        })
        contador_letras += 1

    for _ in range(n_recharge):
        nodos.append({
            "id": numero_a_letras(contador_letras),
            "role": "recharge"
        })
        contador_letras += 1

    for _ in range(n_client):
        tipo_cliente = random.choice(["premium", "normal"])
        nodos.append({
            "id": numero_a_letras(contador_letras),
            "role": "client",
            "client_id": f"C{contador_clientes:03d}",
            "nombre": f"Client{contador_clientes - 1}",
            "tipo": tipo_cliente
        })
        contador_letras += 1
        contador_clientes += 1

    return nodos