import json
import os
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import networkx as nx
from networkx.readwrite import json_graph
import sys

# Add project root to sys.path to allow importing from trabajo_modulado
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from trabajo_modulado.utils.reporting import generate_report_pdf
from trabajo_modulado.model.nodo import generar_nodos # For type hinting if needed, not direct use
from trabajo_modulado.model.order import generar_ordenes # For type hinting
from trabajo_modulado.model.ruta import calcular_costo


DATA_DIR = "api/data"
NODOS_FILE = os.path.join(DATA_DIR, "nodos.json")
ORDENES_FILE = os.path.join(DATA_DIR, "ordenes.json")
RUTAS_USADAS_FILE = os.path.join(DATA_DIR, "rutas_usadas.json")
GRAFO_FILE = os.path.join(DATA_DIR, "grafo.json")

app = FastAPI(title="Correos Chile Drone Simulation API", version="1.0.0")

# --- Pydantic Models ---
class NodeModel(BaseModel):
    id: str
    role: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    client_id: Optional[str] = None
    nombre: Optional[str] = None
    tipo: Optional[str] = None

class OrderModel(BaseModel):
    id: str
    cliente: str
    cliente_id: str
    origen: str
    destino: str
    status: str
    fecha_creacion: str
    prioridad: int
    fecha_entrega: Optional[str] = None
    costo_total: Optional[float] = 0 # Allow float if costs can be non-integer

class ClientDetailModel(NodeModel):
    total_ordenes: Optional[int] = 0

class OrderUpdateStatusModel(BaseModel):
    status: str # "Cancelled" or "Completed"

# --- Data Loading Helper Functions ---
def load_data(file_path: str):
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Data file not found: {os.path.basename(file_path)}. Run simulation first.")
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Error decoding JSON from {os.path.basename(file_path)}.")

def save_data(file_path: str, data: Any):
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving data to {os.path.basename(file_path)}: {e}")

def load_graph():
    data = load_data(GRAFO_FILE)
    return json_graph.node_link_graph(data)

# --- Basic Check Endpoint ---
@app.get("/")
async def read_root():
    return {"message": "Welcome to Correos Chile Drone Simulation API. Visit /docs for API documentation."}

# --- Client Endpoints ---
@app.get("/clients/", response_model=List[ClientDetailModel], tags=["Clients"])
async def get_all_clients():
    """
    Get the list of all registered clients with their total order count.
    """
    nodos_data = load_data(NODOS_FILE)
    ordenes_data = load_data(ORDENES_FILE)
    
    client_nodes = [node for node in nodos_data if node.get("role") == "client"]
    
    # Calculate total orders for each client
    client_order_counts = {}
    for order in ordenes_data:
        client_id = order.get("cliente_id")
        if client_id:
            client_order_counts[client_id] = client_order_counts.get(client_id, 0) + 1
            
    result_clients = []
    for client_node in client_nodes:
        client_id = client_node.get("client_id")
        total_orders = client_order_counts.get(client_id, 0)
        # Create a dictionary from client_node and add total_ordenes
        client_detail = {**client_node, "total_ordenes": total_orders}
        result_clients.append(ClientDetailModel(**client_detail))
        
    return result_clients

@app.get("/clients/{client_id}", response_model=ClientDetailModel, tags=["Clients"])
async def get_client_by_id(client_id: str):
    """
    Get detailed information for a specific client by their Client ID.
    """
    nodos_data = load_data(NODOS_FILE)
    ordenes_data = load_data(ORDENES_FILE) # To calculate total_orders for this specific client

    client_node_data = None
    for node in nodos_data:
        if node.get("role") == "client" and node.get("client_id") == client_id:
            client_node_data = node
            break
    
    if not client_node_data:
        raise HTTPException(status_code=404, detail=f"Client with ID '{client_id}' not found.")

    # Calculate total orders for this specific client
    total_orders = 0
    for order in ordenes_data:
        if order.get("cliente_id") == client_id:
            total_orders += 1
            
    client_detail = {**client_node_data, "total_ordenes": total_orders}
    return ClientDetailModel(**client_detail)

# --- Order Endpoints ---
@app.get("/orders/", response_model=List[OrderModel], tags=["Orders"])
async def get_all_orders():
    """
    List all orders registered in the system.
    """
    ordenes_data = load_data(ORDENES_FILE)
    return [OrderModel(**order) for order in ordenes_data]

@app.get("/orders/orders/{order_id}", response_model=OrderModel, tags=["Orders"])
async def get_order_by_id(order_id: str):
    """
    Get detailed information for a specific order by its ID.
    """
    ordenes_data = load_data(ORDENES_FILE)
    for order in ordenes_data:
        if order.get("id") == order_id:
            return OrderModel(**order)
    raise HTTPException(status_code=404, detail=f"Order with ID '{order_id}' not found.")

@app.post("/orders/orders/{order_id}/cancel", response_model=OrderModel, tags=["Orders"])
async def cancel_order(order_id: str):
    """
    Cancel a specific order. Order must be in 'Pendiente' status.
    """
    ordenes_data = load_data(ORDENES_FILE)
    order_found = False
    updated_order = None

    for order in ordenes_data:
        if order.get("id") == order_id:
            order_found = True
            if order.get("status") == "Pendiente":
                order["status"] = "Cancelled"
                order["fecha_entrega"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Or set to None/CancelDate
                updated_order = order
                break
            else:
                raise HTTPException(status_code=400, detail=f"Order '{order_id}' cannot be cancelled. Status is '{order.get('status')}'.")
    
    if not order_found:
        raise HTTPException(status_code=404, detail=f"Order with ID '{order_id}' not found.")
    
    save_data(ORDENES_FILE, ordenes_data)
    return OrderModel(**updated_order)

@app.post("/orders/orders/{order_id}/complete", response_model=OrderModel, tags=["Orders"])
async def complete_order(order_id: str):
    """
    Mark a specific order as completed. Order must be in 'Pendiente' status.
    """
    ordenes_data = load_data(ORDENES_FILE)
    order_found = False
    updated_order = None

    for order in ordenes_data:
        if order.get("id") == order_id:
            order_found = True
            if order.get("status") == "Pendiente": # Assuming only pending can be completed directly
                order["status"] = "Delivered"
                order["fecha_entrega"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Potentially calculate/update costo_total if not done before
                updated_order = order
                break
            elif order.get("status") == "Delivered":
                 raise HTTPException(status_code=400, detail=f"Order '{order_id}' is already completed.")
            else:
                raise HTTPException(status_code=400, detail=f"Order '{order_id}' cannot be marked as completed. Status is '{order.get('status')}'.")

    if not order_found:
        raise HTTPException(status_code=404, detail=f"Order with ID '{order_id}' not found.")
        
    save_data(ORDENES_FILE, ordenes_data)
    return OrderModel(**updated_order)

# --- Report Endpoints ---
@app.get("/reports/reports/pdf", tags=["Reports"])
async def get_simulation_report_pdf():
    """
    Generate and return a PDF report summarizing system simulation data,
    including routes, clients, nodes, and charts.
    """
    try:
        nodos = load_data(NODOS_FILE)
        ordenes = load_data(ORDENES_FILE)
        rutas_usadas = load_data(RUTAS_USADAS_FILE)
    except HTTPException as e: # Catch if data files are missing
        if e.status_code == 404:
             raise HTTPException(status_code=404, detail="Required data files (nodos, ordenes, rutas_usadas) not found. Run simulation first.")
        raise e # Re-raise other HTTPExceptions from load_data

    if not nodos or not ordenes: # rutas_usadas can be empty
        raise HTTPException(status_code=400, detail="Not enough data to generate a report. Ensure simulation has run and produced nodes and orders.")

    try:
        pdf_buffer = generate_report_pdf(nodos, ordenes, rutas_usadas)
        # pdf_buffer is a BytesIO object
        
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"informe_simulacion_drones_api_{current_time}.pdf"
        
        return FileResponse(
            path=pdf_buffer, 
            media_type='application/pdf', 
            filename=filename
        )
    except Exception as e:
        # Log the exception e for debugging
        print(f"Error generating PDF report: {e}")
        raise HTTPException(status_code=500, detail=f"Could not generate PDF report: {str(e)}")

# --- Info/Stats Endpoints ---
def get_node_visit_counts(rutas_usadas_data: Dict[str, int]) -> Dict[str, int]:
    node_visits = {}
    for ruta_str, freq in rutas_usadas_data.items():
        nodes_in_path = ruta_str.split(" → ")
        for node_id_in_path in nodes_in_path:
            node_visits[node_id_in_path] = node_visits.get(node_id_in_path, 0) + freq
    return node_visits

def get_ranked_nodes_by_role(role: str, nodos_data: List[Dict], node_visits: Dict[str, int]):
    role_nodes_visits = []
    for node in nodos_data:
        if node.get("role") == role:
            node_id = node.get("id")
            visits = node_visits.get(node_id, 0)
            # Include more node details if desired, e.g., name for clients
            client_info = {"id": node_id, "visits": visits}
            if role == "client":
                client_info["name"] = node.get("nombre", "N/A")
                client_info["client_id"] = node.get("client_id", "N/A")
            role_nodes_visits.append(client_info)
            
    return sorted(role_nodes_visits, key=lambda x: x["visits"], reverse=True)

@app.get("/info/reports/visits/clients", response_model=List[Dict], tags=["Info Reports"])
async def get_top_visited_clients():
    """
    Get the ranking of client nodes most visited in simulation routes.
    """
    nodos = load_data(NODOS_FILE)
    rutas_usadas = load_data(RUTAS_USADAS_FILE)
    if not rutas_usadas: # If no routes, then no visits
        return []
    node_visits = get_node_visit_counts(rutas_usadas)
    return get_ranked_nodes_by_role("client", nodos, node_visits)

@app.get("/info/reports/visits/recharges", response_model=List[Dict], tags=["Info Reports"])
async def get_top_visited_recharge_nodes():
    """
    Get the ranking of recharge nodes most visited in simulation routes.
    """
    nodos = load_data(NODOS_FILE)
    rutas_usadas = load_data(RUTAS_USADAS_FILE)
    if not rutas_usadas:
        return []
    node_visits = get_node_visit_counts(rutas_usadas)
    return get_ranked_nodes_by_role("recharge", nodos, node_visits)

@app.get("/info/reports/visits/storages", response_model=List[Dict], tags=["Info Reports"])
async def get_top_visited_storage_nodes():
    """
    Get the ranking of storage nodes most visited in simulation routes.
    """
    nodos = load_data(NODOS_FILE)
    rutas_usadas = load_data(RUTAS_USADAS_FILE)
    if not rutas_usadas:
        return []
    node_visits = get_node_visit_counts(rutas_usadas)
    return get_ranked_nodes_by_role("storage", nodos, node_visits)

@app.get("/info/reports/summary", response_model=Dict[str, Any], tags=["Info Reports"])
async def get_simulation_summary():
    """
    Get a general summary of the active simulation, including node counts,
    order statuses, and route statistics.
    """
    nodos = load_data(NODOS_FILE)
    ordenes = load_data(ORDENES_FILE)
    rutas_usadas = load_data(RUTAS_USADAS_FILE)
    G = load_graph() # For edge count and potentially route cost recalculation

    summary = {}

    # Node summary
    node_roles = {"client": 0, "storage": 0, "recharge": 0, "other": 0}
    for node in nodos:
        role = node.get("role", "other")
        if role in node_roles:
            node_roles[role] += 1
        else:
            node_roles["other"] += 1
    summary["node_counts_by_role"] = node_roles
    summary["total_nodes"] = len(nodos)
    summary["total_edges"] = G.number_of_edges()

    # Order summary
    order_statuses = {}
    for order in ordenes:
        status = order.get("status", "Unknown")
        order_statuses[status] = order_statuses.get(status, 0) + 1
    summary["order_counts_by_status"] = order_statuses
    summary["total_orders"] = len(ordenes)

    # Route summary
    summary["total_unique_routes_used"] = len(rutas_usadas)
    total_route_executions = sum(rutas_usadas.values())
    summary["total_route_executions"] = total_route_executions
    
    if total_route_executions > 0:
        total_hops = 0
        total_cost_of_executed_routes = 0
        for ruta_str, freq in rutas_usadas.items():
            path_nodes = ruta_str.split(" → ")
            total_hops += (len(path_nodes) - 1) * freq
            
            # Calculate cost for this specific path as it was traversed
            # This requires the graph G.
            current_path_cost = 0
            if len(path_nodes) > 1:
                try:
                    current_path_cost = calcular_costo(G, path_nodes) # calcular_costo is from trabajo_modulado.model.ruta
                except Exception: # Broad exception if a node/edge in path_nodes is not in G (should not happen with consistent data)
                    current_path_cost = -1 # Indicate error or missing data for this path cost
            total_cost_of_executed_routes += current_path_cost * freq
            
        summary["average_hops_per_route_execution"] = round(total_hops / total_route_executions, 2) if total_route_executions else 0
        summary["average_cost_per_route_execution"] = round(total_cost_of_executed_routes / total_route_executions, 2) if total_route_executions else 0
    else:
        summary["average_hops_per_route_execution"] = 0
        summary["average_cost_per_route_execution"] = 0
        
    return summary

# Endpoints will be added below this line in subsequent steps.

if __name__ == "__main__":
    import uvicorn
    # Ensure DATA_DIR exists for dev server, though it's created by Streamlit app
    os.makedirs(DATA_DIR, exist_ok=True) 
    uvicorn.run(app, host="0.0.0.0", port=8000)
