import matplotlib.pyplot as plt
import networkx as nx
import streamlit as st
import folium
from streamlit_folium import st_folium

# Temuco's approximate center
TEMUCO_CENTER = [-38.7359, -72.5904]

def visualizar_red(G, ruta=None): # This is the old function, will be replaced by folium map
    pos = nx.spring_layout(G, seed=42)
    role_colors = {"storage": "blue", "recharge": "green", "client": "red"}
    node_colors = [role_colors[G.nodes[n]["role"]] for n in G.nodes]

    plt.figure(figsize=(10,7))
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=300)
    nx.draw_networkx_labels(G, pos)

    edge_labels = nx.get_edge_attributes(G, 'weight')

    if ruta:
        aristas_ruta = list(zip(ruta, ruta[1:]))
        nx.draw_networkx_edges(G, pos, edgelist=aristas_ruta, edge_color='orange', width=3)
        otras_aristas = [e for e in G.edges if e not in aristas_ruta and (e[1], e[0]) not in aristas_ruta]
        nx.draw_networkx_edges(G, pos, edgelist=otras_aristas, alpha=0.3)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    else:
        nx.draw_networkx_edges(G, pos, alpha=0.5)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

    plt.title("Red de Drones - Nodos coloreados por rol")
    plt.axis('off')
    st.pyplot(plt.gcf())


def visualizar_mapa_folium(G, ruta=None, mst_edges=None):
    # Create a Folium map centered on Temuco
    m = folium.Map(location=TEMUCO_CENTER, zoom_start=13)

    role_colors_map = {"storage": "blue", "recharge": "green", "client": "red", "default": "gray"}
    node_info = G.nodes(data=True)

    # Add nodes to the map
    for node_id, data in node_info:
        lat = data.get("lat")
        lon = data.get("lon")
        role = data.get("role", "default")
        color = role_colors_map.get(role, "gray")
        
        if lat is not None and lon is not None:
            tooltip_text = f"ID: {node_id}<br>Role: {role}"
            if role == "client":
                tooltip_text += f"<br>Client ID: {data.get('client_id', 'N/A')}"
                tooltip_text += f"<br>Name: {data.get('nombre', 'N/A')}"
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=5,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                tooltip=tooltip_text
            ).add_to(m)

    # Add all edges to the map (thin gray lines)
    for u, v, data in G.edges(data=True):
        u_data = G.nodes[u]
        v_data = G.nodes[v]
        if all(k in u_data for k in ("lat", "lon")) and all(k in v_data for k in ("lat", "lon")):
            points = [(u_data["lat"], u_data["lon"]), (v_data["lat"], v_data["lon"])]
            folium.PolyLine(points, color="gray", weight=1, opacity=0.5).add_to(m)

    # Highlight MST edges if provided (thicker, distinct color e.g., purple)
    if mst_edges:
        for u, v in mst_edges:
            u_data = G.nodes[u]
            v_data = G.nodes[v]
            if all(k in u_data for k in ("lat", "lon")) and all(k in v_data for k in ("lat", "lon")):
                points = [(u_data["lat"], u_data["lon"]), (v_data["lat"], v_data["lon"])]
                folium.PolyLine(points, color="purple", weight=3, opacity=0.8, tooltip=f"MST Edge: {u}-{v}").add_to(m)
    
    # Highlight the specific route if provided (thicker, distinct color e.g., orange)
    if ruta:
        aristas_ruta = list(zip(ruta, ruta[1:]))
        for u, v in aristas_ruta:
            u_data = G.nodes[u]
            v_data = G.nodes[v]
            if all(k in u_data for k in ("lat", "lon")) and all(k in v_data for k in ("lat", "lon")):
                points = [(u_data["lat"], u_data["lon"]), (v_data["lat"], v_data["lon"])]
                folium.PolyLine(points, color="orange", weight=4, opacity=1, tooltip=f"Route: {u} → {v}").add_to(m)

    # Display the map in Streamlit
    st_folium(m, width=700, height=500)


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
