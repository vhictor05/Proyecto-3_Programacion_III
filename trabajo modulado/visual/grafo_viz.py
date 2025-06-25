import matplotlib.pyplot as plt
import networkx as nx
import streamlit as st


def visualizar_red(G, ruta=None):
    pos = nx.spring_layout(G, seed=42)
    role_colors = {"storage": "orange", "recharge": "blue", "client": "green"}
    node_colors = [role_colors[G.nodes[n]["role"]] for n in G.nodes]

    plt.figure(figsize=(10,7))
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=300)
    nx.draw_networkx_labels(G, pos)

    edge_labels = nx.get_edge_attributes(G, 'weight')

    if ruta:
        aristas_ruta = list(zip(ruta, ruta[1:]))
        nx.draw_networkx_edges(G, pos, edgelist=aristas_ruta, edge_color='red', width=3)
        otras_aristas = [e for e in G.edges if e not in aristas_ruta and (e[1], e[0]) not in aristas_ruta]
        nx.draw_networkx_edges(G, pos, edgelist=otras_aristas, alpha=0.3)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    else:
        nx.draw_networkx_edges(G, pos, alpha=0.5)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

    plt.title("Red de Drones - Nodos coloreados por rol")
    plt.axis('off')
    st.pyplot(plt.gcf())

def asignar_etiquetas_cortas(nodos_ids):
    """
    Dado un listado de nodos IDs, asigna etiquetas tipo letras Excel A, B, ..., Z, AA, AB,...
    Retorna diccionario: nodo_id -> etiqueta_corta
    """
    def numero_a_letras(num):
        letras = ""
        while num > 0:
            num -= 1
            letras = chr(ord('A') + (num % 26)) + letras
            num //= 26
        return letras

    etiquetas = {}
    for i, nodo in enumerate(sorted(nodos_ids), start=1):
        etiquetas[nodo] = numero_a_letras(i)
    return etiquetas

    add_edges(root)
    return G

def node_label(node):
    ruta_str = node.key[1]  # ruta en segundo elemento
    return f"{ruta_str}\nFreq: {node.freq}"


def avl_to_networkx(root):
    G = nx.DiGraph()

    def add_edges(node):
        if not node:
            return
        label = node_label(node)
        G.add_node(label)
        if node.left:
            left_label = node_label(node.left)
            G.add_edge(label, left_label)
            add_edges(node.left)
        if node.right:
            right_label = node_label(node.right)
            G.add_edge(label, right_label)
            add_edges(node.right)

    add_edges(root)
    return G

def assign_positions(root):
    positions = {}
    def _assign(node, depth, pos):
        if node is None:
            return
        label = node_label(node)
        positions[label] = (pos, -depth)
        offset = 1 / (depth + 2)
        _assign(node.left, depth + 1, pos - offset)
        _assign(node.right, depth + 1, pos + offset)
    _assign(root, 0, 0.5)
    return positions

def visualizar_avl(root):
    if not root:
        st.info("El árbol AVL está vacío.")
        return

    G = avl_to_networkx(root)
    pos = assign_positions(root)

    plt.figure(figsize=(12, 8))
    nx.draw(G, pos, with_labels=True, node_size=2500, node_color="lightblue",
            font_size=8, font_weight="bold", arrows=True)
    st.pyplot(plt.gcf())
