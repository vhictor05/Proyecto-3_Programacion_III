import networkx as nx
import numpy as np

def generar_aristas_aleatorias(nodos, m):
    G = nx.Graph()
    for nodo in nodos:
        G.add_node(nodo["id"], role=nodo["role"])
    nodos_ids = [n["id"] for n in nodos]
    for i in range(len(nodos_ids)-1):
        G.add_edge(nodos_ids[i], nodos_ids[i+1], weight=np.random.randint(1,10))
    while G.number_of_edges() < m:
        n1, n2 = np.random.choice(nodos_ids, 2, replace=False)
        if not G.has_edge(n1,n2):
            G.add_edge(n1, n2, weight=np.random.randint(1,10))
    return G
