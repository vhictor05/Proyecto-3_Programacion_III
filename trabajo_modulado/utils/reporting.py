from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
import matplotlib.pyplot as plt
import pandas as pd
from collections import Counter

# Helper function to save matplotlib fig to a BytesIO object to be used by ReportLab Image
def fig_to_img_bytes(fig):
    img_bytes = BytesIO()
    fig.savefig(img_bytes, format='PNG', dpi=300)
    plt.close(fig) # Close the figure to free memory
    img_bytes.seek(0)
    return img_bytes

def generate_report_pdf(nodos, ordenes, rutas_usadas):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("Informe de Simulación Logística de Drones", styles['h1']))
    story.append(Spacer(1, 0.2*inch))

    # --- Section: Rutas Frecuentes ---
    story.append(Paragraph("Rutas Más Frecuentes", styles['h2']))
    if rutas_usadas:
        sorted_rutas = sorted(rutas_usadas.items(), key=lambda item: item[1], reverse=True)
        data = [["Ruta", "Frecuencia"]]
        for ruta, freq in sorted_rutas[:10]: # Display top 10
            data.append([Paragraph(ruta, styles['Normal']), str(freq)])
        
        table_rutas = Table(data, colWidths=[4*inch, 1*inch])
        table_rutas.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(table_rutas)
    else:
        story.append(Paragraph("No hay datos de rutas usadas.", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

    # --- Section: Clientes Más Recurrentes ---
    story.append(Paragraph("Clientes Más Recurrentes (por nº de órdenes)", styles['h2']))
    
    if not ordenes:
        story.append(Paragraph("No hay datos de órdenes.", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
    else:
        df_ordenes = pd.DataFrame(ordenes)
    
        # Validación extra: asegurar que existe cliente_id y que tiene valores válidos
        if 'cliente_id' in df_ordenes.columns and df_ordenes['cliente_id'].notnull().any():
            client_counts = df_ordenes['cliente_id'].value_counts().reset_index()
            client_counts.columns = ['cliente_id', 'total_ordenes']
    
            # Buscar nombres de clientes en nodos
            df_nodos_clientes = pd.DataFrame([n for n in nodos if n.get('role') == 'client'])
            tiene_nombres = (not df_nodos_clientes.empty) and ('client_id' in df_nodos_clientes.columns)
    
            if tiene_nombres:
                client_counts = pd.merge(
                    client_counts,
                    df_nodos_clientes[['client_id', 'nombre']],
                    left_on='cliente_id',
                    right_on='client_id',
                    how='left'
                )
                client_counts['nombre'] = client_counts['nombre'].fillna('N/A')
                data_clients = [["Cliente ID", "Nombre", "Total Órdenes"]]
                for _, row in client_counts.head(10).iterrows():
                    data_clients.append([row['cliente_id'], row['nombre'], str(row['total_ordenes'])])
            else:
                data_clients = [["Cliente ID", "Total Órdenes"]]
                for _, row in client_counts.head(10).iterrows():
                    data_clients.append([row['cliente_id'], str(row['total_ordenes'])])
    
            table_clients = Table(
                data_clients,
                colWidths=[1*inch, 2.5*inch, 1.5*inch] if len(data_clients[0]) == 3 else [2*inch, 2*inch]
            )
            table_clients.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table_clients)
        else:
            story.append(Paragraph("No hay datos válidos de 'cliente_id' en las órdenes para generar este reporte.", styles['Normal']))
    
    story.append(Spacer(1, 0.2*inch))

    # --- Section: Nodos Más Utilizados ---
    story.append(Paragraph("Nodos Más Utilizados (en rutas)", styles['h2']))
    if rutas_usadas:
        node_visits = Counter()
        for ruta_str, freq in rutas_usadas.items():
            nodes_in_path = ruta_str.split(" → ")
            for node_id in nodes_in_path:
                node_visits[node_id] += freq
        
        sorted_node_visits = node_visits.most_common(10) # Top 10 visited nodes
        data_nodes = [["Nodo ID", "Rol", "Visitas"]]
        node_roles = {n['id']: n['role'] for n in nodos}
        for node_id, visits in sorted_node_visits:
            role = node_roles.get(node_id, 'Desconocido')
            data_nodes.append([node_id, role, str(visits)])
        
        table_nodes = Table(data_nodes, colWidths=[1.5*inch, 1.5*inch, 1*inch])
        table_nodes.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(table_nodes)
    else:
        story.append(Paragraph("No hay datos de rutas usadas para calcular visitas a nodos.", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

    # --- Section: Gráficas ---
    story.append(Paragraph("Gráficas del Sistema", styles['h2']))
    if nodos:
        # Pie chart: Proportion of nodes by role
        roles = [n["role"] for n in nodos]
        role_counts = Counter(roles)
        
        fig_pie, ax_pie = plt.subplots(figsize=(5, 4)) # Adjusted size for PDF
        ax_pie.pie(role_counts.values(), labels=role_counts.keys(), autopct='%1.1f%%', startangle=90)
        ax_pie.axis('equal')
        ax_pie.set_title("Distribución de Nodos por Rol")
        
        img_pie_data = fig_to_img_bytes(fig_pie)
        story.append(Image(img_pie_data, width=4*inch, height=3.2*inch)) # Adjusted size
        story.append(Spacer(1, 0.2*inch))

        # Bar chart: Comparison of visits for top N nodes (if rutas_usadas)
        if rutas_usadas and node_visits: # node_visits calculated above
            # Separate visits by role for top nodes
            df_all_nodes = pd.DataFrame(nodos)
            
            client_nodes_visits = {nid: node_visits.get(nid,0) for nid in df_all_nodes[df_all_nodes['role']=='client']['id']}
            storage_nodes_visits = {nid: node_visits.get(nid,0) for nid in df_all_nodes[df_all_nodes['role']=='storage']['id']}
            recharge_nodes_visits = {nid: node_visits.get(nid,0) for nid in df_all_nodes[df_all_nodes['role']=='recharge']['id']}

            top_n = 5
            top_clients = Counter(client_nodes_visits).most_common(top_n)
            top_storages = Counter(storage_nodes_visits).most_common(top_n)
            top_recharges = Counter(recharge_nodes_visits).most_common(top_n)
            
            if top_clients or top_storages or top_recharges:
                fig_bar, ax_bar = plt.subplots(figsize=(6, 4)) # Adjusted size
                
                bar_data = {}
                if top_clients:
                    bar_data.update(dict(top_clients))
                if top_storages:
                    bar_data.update(dict(top_storages)) # Note: if node IDs overlap, this will overwrite. Assuming IDs are unique across roles.
                if top_recharges:                                 # If node IDs can be e.g. "N1" for client and "N1" for storage, this needs care.
                    bar_data.update(dict(top_recharges))      # For this project, node IDs are unique (A, B, C...).

                node_ids_for_bar = list(bar_data.keys())
                visit_counts_for_bar = list(bar_data.values())
                colors_for_bar = []
                for nid in node_ids_for_bar:
                    role = df_all_nodes[df_all_nodes['id'] == nid]['role'].iloc[0]
                    if role == 'client': colors_for_bar.append('red')
                    elif role == 'storage': colors_for_bar.append('blue')
                    elif role == 'recharge': colors_for_bar.append('green')
                    else: colors_for_bar.append('gray')

                ax_bar.bar(node_ids_for_bar, visit_counts_for_bar, color=colors_for_bar)
                ax_bar.set_xlabel("Nodo ID")
                ax_bar.set_ylabel("Número de Visitas")
                ax_bar.set_title(f"Top Nodos Visitados (hasta N={top_n} por categoría)")
                plt.xticks(rotation=45, ha="right")
                plt.tight_layout() # Important for labels not getting cut off

                img_bar_data = fig_to_img_bytes(fig_bar)
                story.append(Image(img_bar_data, width=5.5*inch, height=3.7*inch)) # Adjusted size
            else:
                story.append(Paragraph("No hay suficientes datos de visitas para generar el gráfico de barras de nodos.", styles['Normal']))
        else:
            story.append(Paragraph("No hay datos de rutas usadas para generar el gráfico de barras de visitas a nodos.", styles['Normal']))
    else:
        story.append(Paragraph("No hay datos de nodos para generar gráficas.", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer
