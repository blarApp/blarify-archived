from .LspCaller import LspCaller
from Files import File
from .SymbolKind import SymbolKind
from Graph.Node import NodeFactory, FileNode, Node
from Graph.Relationship import RelationshipCreator, RelationshipType
from .ContextTracker import ContextTracker
from typing import List


class SymbolGetter:
    @staticmethod
    def get_symbol_start_position(symbol: dict):
        return symbol["location"]["range"]["start"]

    @staticmethod
    def get_symbol_end_position(symbol: dict):
        return symbol["location"]["range"]["end"]

    @staticmethod
    def get_symbol_uri(symbol: dict):
        return symbol["location"]["uri"]

    @staticmethod
    def get_symbol_kind_as_SymbolKind(symbol: dict):
        return SymbolKind(symbol["kind"])

    @staticmethod
    def get_symbol_name(symbol: dict):
        return symbol["name"]

    @staticmethod
    def get_symbol_start_line(symbol: dict):
        return symbol["location"]["range"]["start"]["line"]

    @staticmethod
    def get_symbol_end_line(symbol: dict):
        return symbol["location"]["range"]["end"]["line"]


class DefinitionGetter:
    @staticmethod
    def get_definition_uri(definition: dict):
        return definition["uri"]


class LspQueryHelper:
    def __init__(self, lsp_caller: LspCaller):
        self.lsp_caller = lsp_caller

    def start(self):
        self.lsp_caller.connect()
        self.lsp_caller.initialize()

    # Document symbols are symbols that are declared in a file, this includes classes, functions, methods but also imports
    def create_document_symbols_nodes_for_file_node(self, file: FileNode):
        symbols = self.lsp_caller.get_document_symbols(file.uri_path)
        if not symbols:
            return [], []
        return self._get_all_symbols_as_nodes(symbols)

    def _get_all_symbols_as_nodes(self, symbols):
        nodes = []
        relationships = []
        for symbol in symbols:
            start_position = SymbolGetter.get_symbol_start_position(symbol)
            uri = SymbolGetter.get_symbol_uri(symbol)
            kind = SymbolGetter.get_symbol_kind_as_SymbolKind(symbol)
            name = SymbolGetter.get_symbol_name(symbol)

            definition = self.lsp_caller.get_declaration(uri, start_position)

            # print()
            # print("References for symbol", name, ":", references)
            # print("Definition for symbol", name, ":", definition)

            if not definition:
                print("No definition found for symbol", name, "at", uri)
                continue

            definition_uri = DefinitionGetter.get_definition_uri(definition)
            node = NodeFactory.create_node_based_on_kind(kind, name, definition_uri)
            if node:
                nodes.append(node)

                # references_paths = self._get_references_paths(references)

                # relationships = (
                #     RelationshipCreator._create_relationships_from_references(
                #         set(references_paths), node
                #     )
                # )

        return nodes

    def _remove_declaration_from_references(
        self, references: List[dict], declaration: dict
    ):
        return [reference for reference in references if reference != declaration]

    def _get_references_paths(self, references: List[dict]):
        return [reference["uri"] for reference in references]
