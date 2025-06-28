def calcular_visitas_por_nodo(rutas_usadas, nodos):
    role_por_nodo = { n["id"]: n["role"] for n in nodos }
    visitas = { n["id"]: 0 for n in nodos }

    for ruta_str, freq in rutas_usadas.items():
        lista_nodos = [s.strip() for s in ruta_str.split("→")]
        for nodo_id in lista_nodos:
            if nodo_id in visitas:
                visitas[nodo_id] += freq

    visitas_clientes = { nid: visitas[nid] for nid in visitas if role_por_nodo.get(nid) == "client" }
    visitas_recharge = { nid: visitas[nid] for nid in visitas if role_por_nodo.get(nid) == "recharge" }
    visitas_storage = { nid: visitas[nid] for nid in visitas if role_por_nodo.get(nid) == "storage" }

    return visitas_clientes, visitas_recharge, visitas_storage
