import sys
import os
import json # For saving data for API
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
from visual.grafo_viz import visualizar_mapa_folium, visualizar_avl
from utils.helpers import calcular_visitas_por_nodo
from model.grafo import generar_aristas_aleatorias, kruskal_mst
from model.ruta import encontrar_ruta_con_bateria, dijkstra_with_battery, get_floyd_warshall_paths, reconstruct_path_from_floyd_warshall, calcular_costo
from utils.reporting import generate_report_pdf # Added PDF report generator

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

        # --- Save data for API ---
        api_data_path = "api/data"
        os.makedirs(api_data_path, exist_ok=True)
        try:
            with open(os.path.join(api_data_path, "nodos.json"), "w") as f:
                json.dump(nodos, f, indent=4)
            with open(os.path.join(api_data_path, "ordenes.json"), "w") as f:
                json.dump(ordenes, f, indent=4)
            with open(os.path.join(api_data_path, "rutas_usadas.json"), "w") as f:
                json.dump(rutas_usadas, f, indent=4)
            
            # Serialize graph: NetworkX's node_link_data is a good choice for JSON
            graph_data = nx.node_link_data(G)
            with open(os.path.join(api_data_path, "grafo.json"), "w") as f:
                json.dump(graph_data, f, indent=4)
            st.toast("Datos de simulación guardados para la API.", icon="💾")
        except Exception as e:
            st.error(f"Error al guardar datos para la API: {e}")
        # --- End save data for API ---




with tabs[1]:
    st.header("Network Visualization")
    if "grafo" in st.session_state and "ordenes" in st.session_state:
        G = st.session_state["grafo"]
        nodos_ids = list(G.nodes)
        nodos_data_list = st.session_state.get("nodos", [])
        node_attr_map = {n['id']: n for n in nodos_data_list}
        
        for node_id_in_graph in G.nodes():
            if node_id_in_graph in node_attr_map:
                # Update the node in G with all attributes from the nodos_data_list entry
                # This includes 'lat', 'lon', 'client_id', 'nombre', 'tipo', etc.
                G.nodes[node_id_in_graph].update(node_attr_map[node_id_in_graph])
            else:
                # This case should ideally not happen if nodos and G are consistent
                # but good to be aware of. It means a node in G has no corresponding entry in nodos_data_list.
                # Ensure 'lat' and 'lon' are at least None if not found, to avoid KeyErrors later
                if 'lat' not in G.nodes[node_id_in_graph]: G.nodes[node_id_in_graph]['lat'] = None
                if 'lon' not in G.nodes[node_id_in_graph]: G.nodes[node_id_in_graph]['lon'] = None

        col1, col2 = st.columns([3, 1])

        with col1:
            # Decide whether to show MST or current route
            show_mst = st.session_state.get("show_mst", False)
            mst_edges_to_display = st.session_state.get("mst_edges", None) if show_mst else None
            
            current_route_to_display = st.session_state.get("ruta_actual", None)
            if show_mst and mst_edges_to_display: # Prioritize showing MST if active
                visualizar_mapa_folium(G, mst_edges=mst_edges_to_display)
                st.caption("Displaying Minimum Spanning Tree (MST) via Kruskal's Algorithm.")
            elif current_route_to_display:
                visualizar_mapa_folium(G, ruta=current_route_to_display)
                st.caption(f"Displaying route: {' → '.join(current_route_to_display)}")
            else:
                visualizar_mapa_folium(G)
                st.caption("Displaying full network. Calculate a route or MST to highlight.")

        with col2:
            origen = st.selectbox("Nodo Origen", nodos_ids, key="origen_select")
            destino = st.selectbox("Nodo Destino", nodos_ids, key="destino_select")
            
            algorithm_options = ["Optimized with Battery (Custom BFS)", "Dijkstra with Battery", "Floyd-Warshall (Weight Only)"]
            selected_algorithm = st.radio("Choose Pathfinding Algorithm:", algorithm_options, index=0, key="algo_select")

            if st.button("Calculate Route", key="calc_route_new"): # Changed key to avoid conflict if old button state exists
                st.session_state["ruta_actual"] = None # Reset previous route
                st.session_state["show_mst"] = False # Clear MST display
                st.session_state["mst_edges"] = None

                if origen == destino:
                    st.warning("Origen y destino deben ser diferentes.")
                else:
                    ruta, costo = None, None
                    if selected_algorithm == "Optimized with Battery (Custom BFS)":
                        ruta, costo = encontrar_ruta_con_bateria(G, origen, destino)
                        if ruta:
                            st.success(f"Ruta (Custom BFS): {' → '.join(ruta)} | Costo: {costo}")
                        else:
                            st.error("No se encontró ruta válida con Custom BFS y restricción de batería.")
                    
                    elif selected_algorithm == "Dijkstra with Battery":
                        # MAX_BATTERY is available from model.ruta, but good to have it accessible or passed if configurable
                        # from model.ruta import MAX_BATTERY # Not needed if already imported or value is fixed
                        ruta, costo = dijkstra_with_battery(G, origen, destino) # Uses default MAX_BATTERY from ruta.py
                        if ruta:
                            st.success(f"Ruta (Dijkstra with Battery): {' → '.join(ruta)} | Costo: {costo}")
                        else:
                            st.error("No se encontró ruta válida con Dijkstra y restricción de batería.")

                    elif selected_algorithm == "Floyd-Warshall (Weight Only)":
                        # Compute FW if not already in session state or if graph changed (not explicitly checked here)
                        if "fw_predecessors" not in st.session_state or "fw_distances" not in st.session_state or st.session_state.get("fw_graph_id") != id(G):
                            st.info("Calculando rutas Floyd-Warshall (puede tardar para grafos grandes)...")
                            fw_preds, fw_dists = get_floyd_warshall_paths(G)
                            if fw_preds is not None and fw_dists is not None:
                                st.session_state["fw_predecessors"] = fw_preds
                                st.session_state["fw_distances"] = fw_dists
                                st.session_state["fw_graph_id"] = id(G) # Store ID of graph used for FW
                                st.success("Cálculo de Floyd-Warshall completado y almacenado.")
                            else:
                                st.error("Error al calcular Floyd-Warshall.")
                                # Prevent further execution in this branch if FW failed
                                st.session_state["ruta_actual"] = None
                                st.rerun() 
                        
                        # Proceed if FW data is available
                        if "fw_predecessors" in st.session_state and "fw_distances" in st.session_state:
                            fw_preds = st.session_state["fw_predecessors"]
                            fw_dists = st.session_state["fw_distances"]
                            ruta = reconstruct_path_from_floyd_warshall(fw_preds, origen, destino)
                            
                            if ruta:
                                # Get cost from fw_dists if available and valid
                                if origen in fw_dists and destino in fw_dists[origen]:
                                    costo = fw_dists[origen][destino]
                                    if costo == float('inf'):
                                        st.error(f"No existe ruta de {origen} a {destino} según Floyd-Warshall (distancia infinita).")
                                        ruta = None # Mark ruta as None if path is not valid
                                    else:
                                        st.success(f"Ruta (Floyd-Warshall - Weight Only): {' → '.join(ruta)} | Costo: {costo:.2f}")
                                        st.warning("Nota: La ruta Floyd-Warshall NO considera restricciones de batería.")
                                else: # Should not happen if reconstruct_path worked and returned a path
                                    st.error("Error al obtener el costo de Floyd-Warshall.")
                                    ruta = None
                            else:
                                st.error(f"No se encontró ruta de {origen} a {destino} con Floyd-Warshall.")
                        else: # Should be caught by earlier error message
                            st.error("Datos de Floyd-Warshall no disponibles. Intente de nuevo.")

                    if ruta:
                        st.session_state["ruta_actual"] = ruta
                    else:
                        st.session_state["ruta_actual"] = None
                    st.rerun() # Rerun to update map display based on new ruta_actual

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
            if "ruta_actual" in st.session_state and st.session_state["ruta_actual"] and not st.session_state.get("show_mst", False):
                st.success(f"Ruta actual: {' → '.join(st.session_state['ruta_actual'])}")
            elif st.session_state.get("show_mst", False) and "mst_edges" in st.session_state:
                 st.success(f"Mostrando MST con {len(st.session_state['mst_edges'])} aristas.")
            else:
                st.info("Calcula una ruta o MST para verla aquí.")

            st.markdown("---") # Separator
            if st.button("🌳 Show Minimum Spanning Tree (Kruskal)", key="show_mst_btn"):
                if G:
                    mst_edges = kruskal_mst(G)
                    st.session_state["mst_edges"] = mst_edges
                    st.session_state["show_mst"] = True
                    st.session_state["ruta_actual"] = None # Clear current route when showing MST
                    st.rerun()
                else:
                    st.warning("El grafo no está disponible. Inicia una simulación.")
            
            if st.session_state.get("show_mst", False):
                if st.button("Clear MST Display", key="clear_mst_btn"):
                    st.session_state["show_mst"] = False
                    st.session_state["mst_edges"] = None
                    st.rerun()

    else:
        st.info("Primero inicializa la simulación en la pestaña 'Run Simulation'.") # Corrected message placement

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
        # Added "cliente_id" to the list of columns for the orders table
        st.table(df_ordenes[["id", "cliente", "cliente_id", "origen", "destino", "status", "fecha_creacion", "prioridad", "fecha_entrega", "costo_total"]].rename(columns={
            "id": "Order ID",
            "cliente": "Cliente Nombre",
            "cliente_id": "Cliente ID",
            "origen": "Origen (Nodo ID)",
            "destino": "Destino (Nodo ID)",
            "status": "Status",
            "fecha_creacion": "Fecha Creación",
            "prioridad": "Prioridad",
            "fecha_entrega": "Fecha Entrega",
            "costo_total": "Costo Total"
        }))
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

    st.markdown("---")
    st.subheader("📄 Generar Informe PDF del Sistema")
    if rutas_usadas and "nodos" in st.session_state and "ordenes" in st.session_state:
        if st.button("Generar y Descargar PDF", key="pdf_report_button"):
            with st.spinner("Generando PDF... esto puede tardar unos segundos."):
                nodos_report = st.session_state["nodos"]
                ordenes_report = st.session_state["ordenes"]
                # rutas_usadas is already available
                
                pdf_buffer = generate_report_pdf(nodos_report, ordenes_report, rutas_usadas)
                
                st.download_button(
                    label="📥 Descargar Informe PDF",
                    data=pdf_buffer,
                    file_name=f"informe_simulacion_drones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf"
                )
                st.success("¡Informe PDF listo para descargar!")
    else:
        st.info("Se requieren datos de simulación (nodos, órdenes y rutas usadas) para generar el informe PDF.")

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
