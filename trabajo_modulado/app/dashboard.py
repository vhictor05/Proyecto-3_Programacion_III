import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import networkx as nx
from datetime import datetime
from model.nodo import generar_nodos
from model.grafo import generar_aristas_aleatorias
from model.ruta import encontrar_ruta_con_bateria
from model.order import generar_ordenes
from model.avl import AVLTree
from visual.grafo_viz import visualizar_red, visualizar_avl
from utils.helpers import calcular_visitas_por_nodo

st.set_page_config(page_title="Dashboard con 5 Pestañas", layout="wide")

st.title("🚁  Simulador logistico de drones - Correos Chile")
st.markdown("Proporciones de roles de nodo:")
st.markdown("• 📦 Nodo de almacenamiento: 20%")
st.markdown("• ⚡️ Nodo de recarga: 20%")
st.markdown("• 🙍‍♂️ Nodo cliente: 60%")

tabs = st.tabs(["Run Simulation", "Explore Network", "Clients & Orders", "Route Analytics", "Statistics"])

with tabs[0]:
    st.header("⚙️ Iniciar simulación")
    n_nodes = st.slider("Number of Nodes", min_value=10, max_value=150, value=15)
    n_edges = st.slider("Number of Edges", min_value=n_nodes-1, max_value=300, value=20)
    n_orders = st.slider("Number of Orders", min_value=1, max_value=500, value=10)

    if st.button("Iniciar simulación"):
        nodos = generar_nodos(n_nodes)
        G = generar_aristas_aleatorias(nodos, n_edges)
        ordenes = generar_ordenes(n_orders, nodos)

        rutas_usadas = {}
        for orden in ordenes:
            ruta, costo = encontrar_ruta_con_bateria(G, orden["origen"], orden["destino"])
            if ruta:
                ruta_str = " → ".join(ruta)
                rutas_usadas[ruta_str] = rutas_usadas.get(ruta_str, 0) + 1
            else:
                # Si no hay ruta válida, puedes decidir omitir o manejar aparte
                pass

        st.session_state["nodos"] = nodos
        st.session_state["grafo"] = G
        st.session_state["ordenes"] = ordenes
        st.session_state["rutas_usadas"] = rutas_usadas

        st.success(f"Simulación inicializada con {n_nodes} nodos, {n_edges} aristas y {n_orders} órdenes.")




with tabs[1]:
    st.header("Network Visualization")
    if "grafo" in st.session_state and "ordenes" in st.session_state:
        G = st.session_state["grafo"]
        nodos_ids = list(G.nodes)

        col1, col2 = st.columns([3, 1])

        with col1:
            if "ruta_actual" in st.session_state and st.session_state["ruta_actual"]:
                visualizar_red(G, st.session_state["ruta_actual"])
            else:
                visualizar_red(G)

        with col2:
            origen = st.selectbox("Nodo Origen", nodos_ids, key="origen_select")
            destino = st.selectbox("Nodo Destino", nodos_ids, key="destino_select")

            if st.button("Calculate Route", key="calc_route"):
                if origen == destino:
                    st.warning("Origen y destino deben ser diferentes.")
                    st.session_state["ruta_actual"] = None
                else:
                    ruta, costo = encontrar_ruta_con_bateria(G, origen, destino)
                    if ruta is None:
                        st.error("No se encontró una ruta válida con la restricción de batería.")
                        st.session_state["ruta_actual"] = None
                    else:
                        st.success(f"Ruta encontrada: {' → '.join(ruta)} | Costo total: {costo}")
                        st.session_state["ruta_actual"] = ruta

            # Botón Complete Delivery siempre visible
            if st.button("Complete Delivery", key="complete_delivery"):
                ordenes = st.session_state["ordenes"]
                orden_coincidente = None
                for orden in ordenes:
                    if orden["origen"] == origen and orden["destino"] == destino and orden["status"] == "Pendiente":
                        orden_coincidente = orden
                        break
                if orden_coincidente:
                    from datetime import datetime

                    orden_coincidente["status"] = "Delivered"
                    orden_coincidente["fecha_entrega"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.success(f"Orden {orden_coincidente['id']} marcada como entregada en {orden_coincidente['fecha_entrega']}")

                    # Guardar ruta en rutas completadas
                    ruta_actual = st.session_state.get("ruta_actual", None)
    

                    st.session_state["ordenes"] = ordenes
                    st.session_state["ruta_actual"] = None
                else:
                    st.info("No hay ninguna orden pendiente con este origen y destino.")

            # Mostrar ruta actual si existe
            if "ruta_actual" in st.session_state and st.session_state["ruta_actual"]:
                st.success(f"Ruta actual: {' → '.join(st.session_state['ruta_actual'])}")
            else:
                st.info("Calcula una ruta para verla aquí.")
    else:
        st.info("Primero inicializa la simulación en la pestaña 'Run Simulation' y genera órdenes.")

with tabs[2]:
    st.header("Clients and Orders")
    if "nodos" in st.session_state and "ordenes" in st.session_state:
        clientes = [n for n in st.session_state["nodos"] if n["role"] == "client"]
        ordenes = st.session_state["ordenes"]

        import pandas as pd
        df_ordenes = pd.DataFrame(ordenes)
        conteo_ordenes = df_ordenes.groupby("cliente_id").size().reset_index(name="total_ordenes")

        df_clientes = pd.DataFrame(clientes)
        df_clientes = df_clientes.merge(conteo_ordenes, how="left", left_on="client_id", right_on="cliente_id")
        df_clientes["total_ordenes"] = df_clientes["total_ordenes"].fillna(0).astype(int)

        st.subheader("Lista de Clientes Activos con Total de Órdenes")
        st.table(df_clientes[["id", "client_id", "nombre", "tipo", "total_ordenes"]].rename(columns={
            "id": "Nodo ID",
            "client_id": "Client ID",
            "nombre": "Nombre",
            "tipo": "Tipo",
            "total_ordenes": "Total Órdenes"
        }))

        st.subheader("Órdenes Generadas")
        st.table(df_ordenes[["id", "cliente", "origen", "destino", "status", "fecha_creacion", "prioridad", "fecha_entrega", "costo_total"]])
    else:
        st.info("Primero inicializa la simulación en la pestaña 'Run Simulation'.")

with tabs[3]:
    st.header("Route Frequency & History")
    rutas_usadas = st.session_state.get("rutas_usadas", {})

    avl = AVLTree()
    root = None
    rutas_ordenadas = sorted(rutas_usadas.items(), key=lambda x: (len(x[0]), x[0]))

    for ruta, freq in rutas_ordenadas:
        clave = (len(ruta), ruta)
        root = avl.insert(root, clave, freq)

    if rutas_usadas:
        st.subheader("Rutas más frecuentes usadas")
        for ruta, freq in sorted(rutas_usadas.items(), key=lambda x: x[1], reverse=True):
            st.write(f"Ruta: {ruta} | Frecuencia: {freq}")
    else:
        st.info("No hay rutas completadas para mostrar.")

    st.subheader("Visualización del Árbol AVL de Rutas")
    visualizar_avl(root)



from collections import Counter

# ... (resto de imports y pestañas 0–4) ...

from collections import Counter
import matplotlib.pyplot as plt

# …

with tabs[4]:
    st.header("General Statistics")

    # 1. Recuperamos rutas_usadas del session_state (puede estar vacío)
    rutas_usadas = st.session_state.get("rutas_usadas", {})

    if not rutas_usadas:
        st.info("No hay rutas procesadas aún. Inicia la simulación para generar datos.")
    else:
        # 2. Contar cuántas veces aparece cada nodo en todas las rutas
        visit_counts = Counter()
        for ruta_str, freq in rutas_usadas.items():
            # separa "A → B → C" en ["A", "B", "C"]
            nodos_en_ruta = ruta_str.split(" → ")
            for nodo in nodos_en_ruta:
                visit_counts[nodo] += freq

        # 3. Obtener listas de IDs de nodos por rol
        nodos = st.session_state["nodos"]
        clientes_ids = [n["id"] for n in nodos if n["role"] == "client"]
        recarga_ids  = [n["id"] for n in nodos if n["role"] == "recharge"]
        storage_ids  = [n["id"] for n in nodos if n["role"] == "storage"]

        # 4. Construir DataFrames para cada rol, con conteos (0 si no aparece)
        df_clientes = pd.DataFrame({
            "Nodo": clientes_ids,
            "Visitas": [visit_counts.get(nid, 0) for nid in clientes_ids]
        })
        df_recarga = pd.DataFrame({
            "Nodo": recarga_ids,
            "Visitas": [visit_counts.get(nid, 0) for nid in recarga_ids]
        })
        df_storage = pd.DataFrame({
            "Nodo": storage_ids,
            "Visitas": [visit_counts.get(nid, 0) for nid in storage_ids]
        })

        # Ordenar cada DataFrame por “Visitas” descendente para resaltar los más visitados
        df_clientes = df_clientes.sort_values(by="Visitas", ascending=False).reset_index(drop=True)
        df_recarga  = df_recarga.sort_values(by="Visitas", ascending=False).reset_index(drop=True)
        df_storage  = df_storage.sort_values(by="Visitas", ascending=False).reset_index(drop=True)

        # 5. Colocar los tres gráficos de barras en una fila, usando columnas:
        col1, col2, col3 = st.columns([1, 1, 1], gap="small")

        # 5.1 Clientes más visitados (col1)
        with col1:
            st.subheader("Clientes más visitados")
            fig1, ax1 = plt.subplots(figsize=(6, 4))
            ax1.bar(df_clientes["Nodo"], df_clientes["Visitas"], color="red")
            ax1.set_xlabel("Cliente")
            ax1.set_ylabel("Visitas")
            ax1.tick_params(axis="x", rotation=45)
            ax1.set_title("")  # Si quieres un título corto, o déjalo en blanco
            plt.tight_layout()
            st.pyplot(fig1)

        # 5.2 Nodos de recarga más usados (col2)
        with col2:
            st.subheader("Recarga más usada")
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            ax2.bar(df_recarga["Nodo"], df_recarga["Visitas"], color="green")
            ax2.set_xlabel("Recarga")
            ax2.set_ylabel("Visitas")
            ax2.tick_params(axis="x", rotation=45)
            ax2.set_title("") 
            plt.tight_layout()
            st.pyplot(fig2)

        # 5.3 Nodos de almacenamiento más visitados (col3)
        with col3:
            st.subheader("Storage más visitado")
            fig3, ax3 = plt.subplots(figsize=(6, 4))
            ax3.bar(df_storage["Nodo"], df_storage["Visitas"], color="blue")
            ax3.set_xlabel("Storage")
            ax3.set_ylabel("Visitas")
            ax3.tick_params(axis="x", rotation=45)
            ax3.set_title("") 
            plt.tight_layout()
            st.pyplot(fig3)

        # ----------------------------------------------------------------
        # 5.4 Gráfico de tarta con la distribución total de nodos por rol
        # ----------------------------------------------------------------

        # Contar cuántos nodos hay de cada rol en total
        roles = [n["role"] for n in nodos]
        counts = Counter(roles)
        storage_count = counts.get("storage", 0)
        recharge_count = counts.get("recharge", 0)
        client_count   = counts.get("client", 0)

        labels = ["Storage", "Recharge", "Client"]
        sizes  = [storage_count, recharge_count, client_count]

        st.subheader("Distribución de nodos por rol")
        fig_pie, ax_pie = plt.subplots(figsize=(6, 4))
        ax_pie.pie(
            sizes,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90
        )
        ax_pie.axis("equal")
        plt.tight_layout()
        st.pyplot(fig_pie)
