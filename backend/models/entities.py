from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime


class Map(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    image_path: str
    width: int
    height: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

    nodes: List["Node"] = Relationship(back_populates="map")
    edges: List["Edge"] = Relationship(back_populates="map")


class Node(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    map_id: int = Field(foreign_key="map.id", index=True)
    x: float
    y: float
    is_landmark: bool = Field(default=False)
    floor: int = Field(default=1)
    meta: Optional[str] = None  # JSON string (tùy chọn)

    map: Map = Relationship(back_populates="nodes")
    aliases: List["Alias"] = Relationship(back_populates="node")


class Alias(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    node_id: int = Field(foreign_key="node.id", index=True)
    name: str
    norm_name: str = Field(index=True)
    lang: str = "vi"
    weight: float = 1.0
    generated: bool = False
    node: Node = Relationship(back_populates="aliases")


class Edge(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    map_id: int = Field(foreign_key="map.id")
    start_node_id: int = Field(foreign_key="node.id")
    end_node_id: int = Field(foreign_key="node.id")
    floor: int = Field(default=1)
    polyline: str  # JSON
    weight: float
    bidirectional: bool = True
    meta: Optional[str] = None

    map: Map = Relationship(back_populates="edges")


class EdgeBase(SQLModel):
    map_id: int
    start_node_id: int
    end_node_id: int
    polyline: Optional[List[List[float]]] = None
    bidirectional: bool = True
    meta: Optional[dict] = None
    floor: Optional[int] = None
