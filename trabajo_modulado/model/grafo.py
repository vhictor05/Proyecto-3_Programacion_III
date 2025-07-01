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

def kruskal_mst(G):
    """
    Calculates the Minimum Spanning Tree (MST) using Kruskal's algorithm.
    Assumes G is a NetworkX graph where edges have a 'weight' attribute.
    Returns a list of edges (u, v) forming the MST.
    """
    # A class to represent a disjoint set
    class DisjointSet:
        def __init__(self, nodes):
            self.parent = {node: node for node in nodes}
            self.rank = {node: 0 for node in nodes}

        def find(self, node):
            if self.parent[node] == node:
                return node
            self.parent[node] = self.find(self.parent[node]) # Path compression
            return self.parent[node]

        def union(self, node1, node2):
            root1 = self.find(node1)
            root2 = self.find(node2)
            if root1 != root2:
                # Union by rank
                if self.rank[root1] < self.rank[root2]:
                    self.parent[root1] = root2
                elif self.rank[root1] > self.rank[root2]:
                    self.parent[root2] = root1
                else:
                    self.parent[root2] = root1
                    self.rank[root1] += 1
                return True
            return False

    if not G.nodes:
        return []

    mst_edges = []
    # Get all edges with their weights: (weight, u, v)
    edges = sorted([(data['weight'], u, v) for u, v, data in G.edges(data=True)])
    
    disjoint_set = DisjointSet(G.nodes())
    
    for weight, u, v in edges:
        if disjoint_set.union(u, v):
            mst_edges.append((u, v))
            # Optimization: if we have N-1 edges for N nodes, MST is complete
            if len(mst_edges) == len(G.nodes()) - 1:
                break
                
    return mst_edges
