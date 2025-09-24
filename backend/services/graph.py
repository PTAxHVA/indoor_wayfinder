from typing import Tuple, List
import json
import networkx as nx
from sqlmodel import Session, select
from backend.models.entities import Node, Edge


def build_graph_for_map(session: Session, map_id: int) -> Tuple[nx.Graph, dict]:
    """
    Trả về:
      - G: networkx.Graph() với trọng số 'weight'
      - node_pos: dict { node_id: (x,y) } để dùng cho sinh hướng đi/nearby landmark
    """
    G = nx.Graph()
    # nạp nodes
    nodes = session.exec(select(Node).where(Node.map_id == map_id)).all()
    node_pos = {n.id: (n.x, n.y) for n in nodes}
    for n in nodes:
        G.add_node(n.id)

    # nạp edges
    edges = session.exec(select(Edge).where(Edge.map_id == map_id)).all()
    for e in edges:
        poly = json.loads(e.polyline)
        w = e.weight
        # cạnh xuôi
        G.add_edge(e.start_node_id, e.end_node_id, weight=w, polyline=poly, edge_id=e.id)

        if e.bidirectional:
            G.add_edge(
                e.end_node_id,
                e.start_node_id,
                weight=w,
                polyline=list(reversed(poly)),
                edge_id=e.id,
            )

    return G, node_pos
