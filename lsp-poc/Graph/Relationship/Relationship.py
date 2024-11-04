from Graph.Relationship import RelationshipType
from Graph.Node import Node


class Relationship:
    start_node: Node
    end_node: Node
    rel_type: RelationshipType

    def __init__(self, start_node: Node, end_node: Node, rel_type: RelationshipType):
        self.start_node = start_node
        self.end_node = end_node
        self.rel_type = rel_type

    @property
    def id(self) -> str:
        return self.__str__()

    def as_object(self) -> dict:
        return {
            "sourceId": self.start_node.id,
            "targetId": self.end_node.id,
            "type": self.rel_type.name,
        }

    def __str__(self) -> str:
        return f"{self.start_node} --[{self.rel_type}]-> {self.end_node}"
