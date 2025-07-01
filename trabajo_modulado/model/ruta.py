from collections import deque
import heapq
import networkx as nx # For Floyd-Warshall later

MAX_BATTERY = 50 # Default max battery

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


def dijkstra_with_battery(G, origen, destino, max_battery_allowance=MAX_BATTERY):
    """
    Calculates the shortest path from origen to destino using Dijkstra's algorithm,
    considering battery constraints and recharge nodes.

    Args:
        G (nx.Graph): The graph. Nodes must have a 'role' attribute. Edges must have 'weight'.
        origen (node_id): Starting node.
        destino (node_id): Target node.
        max_battery_allowance (int): Maximum battery capacity for the drone.

    Returns:
        tuple: (path, cost) if a path is found, otherwise (None, None).
               path is a list of node_ids.
               cost is the total weight of the path.
    """
    recargas = {n for n, d in G.nodes(data=True) if d.get('role') == 'recharge'}

    # Priority queue stores: (cost, battery_spent_on_segment, current_node, path_taken)
    # cost: total accumulated weight of the path
    # battery_spent_on_segment: energy consumed since last recharge or start
    # current_node: the node itself
    # path_taken: list of nodes from origin to current_node
    pq = [(0, 0, origen, [origen])]  # (total_cost, battery_on_segment, node, path)

    # Visited set stores tuples of (node, battery_spent_on_segment_at_arrival)
    # This is crucial: we might revisit a node if we arrive with a better battery state (less spent on current segment)
    # or lower total cost.
    # However, for Dijkstra, we only care about the minimum cost to reach a node.
    # The state needs to capture enough to make valid decisions.
    # Let's use: visited_min_cost[node] = min_cost_to_reach_node
    # But battery constraint is per segment.
    # A better visited for this problem: visited[(node, battery_spent_on_segment)] = cost
    # Simpler: visited_costs[node] = (min_cost_to_reach_node, min_battery_spent_on_segment_at_that_cost)
    # For standard Dijkstra, we only add to PQ if a shorter path is found.
    # Here, a path might be longer but feasible due to battery, or shorter but infeasible.

    # visited dictionary: node -> (min_total_cost_to_reach_node, battery_spent_on_segment_for_that_cost)
    # This helps avoid cycles and redundant computations if we reach a node via a path
    # that is worse both in terms of total cost and battery spent on the current segment.
    # A simpler approach for Dijkstra: just store min_cost to reach (node, battery_spent_this_segment) state.
    # visited_costs = {} # (node, battery_spent_on_segment) -> min_total_cost

    # Let's refine `visited`: store (cost_to_reach_node, battery_spent_on_segment_when_reaching_node)
    # And only push to PQ if we find a better way to reach `(neighbor, new_battery_on_segment)`
    # or the same way with less total_cost.
    # `dist` will store the minimum cost found so far to reach a state (node, battery_on_segment)
    # dist[(node, battery_on_segment)] = total_cost
    dist = {}
    dist[(origen, 0)] = 0


    while pq:
        total_cost, battery_on_segment, current_node, path = heapq.heappop(pq)

        # If this path to (current_node, battery_on_segment) is already worse than a known one, skip.
        if total_cost > dist.get((current_node, battery_on_segment), float('inf')):
            continue

        if current_node == destino:
            return path, total_cost

        for neighbor in G.neighbors(current_node):
            edge_weight = G.edges[current_node, neighbor].get('weight', 1)
            new_total_cost = total_cost + edge_weight

            # Determine battery consumption for the next segment
            if neighbor in recargas:
                new_battery_on_segment = 0 # Battery resets *after* arriving at recharge, effectively 0 for next hop from here
                                          # For path planning, this means the segment to the recharge node must be possible,
                                          # then from recharge node, battery is full.
                                          # The cost to reach the recharge node is `edge_weight`.
                                          # The battery spent to reach `neighbor` (recharge) is `battery_on_segment + edge_weight`.
                battery_to_reach_neighbor = battery_on_segment + edge_weight
                battery_for_next_segment_from_neighbor = 0 # Correct: effectively starts fresh
            else:
                battery_to_reach_neighbor = battery_on_segment + edge_weight
                battery_for_next_segment_from_neighbor = battery_to_reach_neighbor


            if battery_to_reach_neighbor <= max_battery_allowance:
                # If we found a cheaper way to reach this state (neighbor, battery_for_next_segment_from_neighbor)
                current_min_cost_to_state = dist.get((neighbor, battery_for_next_segment_from_neighbor), float('inf'))
                if new_total_cost < current_min_cost_to_state:
                    dist[(neighbor, battery_for_next_segment_from_neighbor)] = new_total_cost
                    heapq.heappush(pq, (new_total_cost, battery_for_next_segment_from_neighbor, neighbor, path + [neighbor]))
    
    return None, None


def get_floyd_warshall_paths(G):
    """
    Calculates all-pairs shortest paths using Floyd-Warshall algorithm from NetworkX.
    This version DOES NOT consider battery constraints, only edge weights.

    Args:
        G (nx.Graph): The graph. Edges must have 'weight'.

    Returns:
        tuple: (predecessors, distances)
               predecessors: A dict-of-dicts of predecessors in shortest paths.
               distances: A dict-of-dicts of shortest path lengths.
               Returns (None, None) if graph is empty or error occurs.
    """
    if not G or not G.nodes:
        return None, None
    try:
        # For undirected graphs, NetworkX's floyd_warshall functions work fine.
        # It computes shortest path distances. For paths, we need predecessors.
        predecessors, distances = nx.floyd_warshall_predecessor_and_distance(G, weight='weight')
        return predecessors, distances
    except nx.NetworkXError as e:
        # Handle cases like disconnected graphs if needed, though FW usually returns inf.
        print(f"Error during Floyd-Warshall calculation: {e}")
        return None, None

def reconstruct_path_from_floyd_warshall(predecessors, source, target):
    """
    Reconstructs a shortest path from a source to a target node given the
    predecessor matrix from Floyd-Warshall.

    Args:
        predecessors (dict): Predecessor matrix (dict-of-dicts).
        source (node_id): Starting node.
        target (node_id): Target node.

    Returns:
        list: The path as a list of node_ids, or None if no path exists.
    """
    if not predecessors or source not in predecessors or target not in predecessors[source]:
        return None
    if predecessors[source].get(target) is None and source != target: # No path
         # Check if target is reachable at all from source in predecessors
        if target not in predecessors[source] or predecessors[source][target] is None:
            # Check if they are in different connected components
            # This check is tricky as FW gives predecessors even for inf distances if path existed before negative cycle
            # For positive weights / no negative cycles, if predecessors[source][target] is None, no path.
            return None


    path = [target]
    curr = target
    try:
        while curr != source:
            prev_node = predecessors[source].get(curr)
            if prev_node is None: # Should not happen if a path exists and target != source
                # This means target is not reachable from source
                return None 
            path.insert(0, prev_node)
            curr = prev_node
            if len(path) > len(predecessors): # Safety break for potential cycles if data is weird
                print("Path reconstruction seems to be in a loop.")
                return None 
    except KeyError: # If a node in path is not in predecessors dict for some reason
        return None
    
    return path

