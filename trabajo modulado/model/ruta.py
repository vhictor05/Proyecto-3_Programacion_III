from collections import deque

MAX_BATTERY = 50

def encontrar_ruta_con_bateria(G, origen, destino):
    recargas = {n for n, d in G.nodes(data=True) if d['role'] == 'recharge'}
    
    # Queue con elementos: (nodo_actual, camino, bateria_actual)
    queue = deque()
    queue.append((origen, [origen], 0))
    
    visitados = set()  # Guardamos (nodo, bateria_actual) para evitar ciclos
    
    while queue:
        actual, camino, bateria = queue.popleft()
        
        if actual == destino:
            return camino, calcular_costo(G, camino)
        
        for vecino in G.neighbors(actual):
            peso = G.edges[actual, vecino]['weight']
            
            # Si el nodo vecino es de recarga, bateria se reinicia
            nueva_bateria = peso if vecino in recargas else bateria + peso
            
            if nueva_bateria <= MAX_BATTERY:
                estado = (vecino, nueva_bateria)
                if estado not in visitados:
                    visitados.add(estado)
                    queue.append((vecino, camino + [vecino], nueva_bateria))
                    
    return None, None

def calcular_costo(G, camino):
    return sum(G.edges[camino[i], camino[i+1]]['weight'] for i in range(len(camino)-1))
