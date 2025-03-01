import time
from websockets import ConnectionClosedError
import websockets.sync.client as ws
import json
from blarify.logger import Logger
import logging

logger = logging.getLogger(__name__)

LANGUAGES_ID_MAP = {
    ".tsx": "typescriptreact",
    ".ts": "typescript",
    ".jsx": "javascriptreact",
    ".js": "javascript",
}


class LspCaller:
    root_uri: str
    host: str
    port: int
    websocket: ws.ClientConnection
    unmatched_responses: dict
    lsp_server_name: str
    connection_retries: int

    def __init__(
        self, root_uri: str, host="localhost", port=5000, log=False, lsp_server_name="", connection_retries: int = 3
    ):
        self.host = host or "localhost"
        self.port = port or 5000
        self.root_uri = root_uri
        self.websocket = None
        self.unmatched_responses = {}
        self.lsp_server_name = lsp_server_name
        self.connection_retries = connection_retries

        self._id = 0

    @property
    def id(self) -> int:
        self._id += 1
        return self._id

    def connect(self, retries: int = 0) -> None:
        uri = f"ws://{self.host}:{self.port}"
        uri += self._get_query_params()
        try:
            self.websocket = ws.connect(uri)
        except ConnectionRefusedError:
            logger.info(f"Connection refused to {uri}")
            logger.info(f"Retrying {retries}/{self.connection_retries}")
            if retries < self.connection_retries:
                time.sleep(1)
                self.connect(retries + 1)

    def _get_query_params(self) -> str:
        if self.lsp_server_name:
            return f"?name={self.lsp_server_name}"
        return ""

    def initialize(self) -> None:
        initialize_request = {
            "jsonrpc": "2.0",
            "id": self.id,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": self.root_uri,
                "capabilities": {},
                "initializationOptions": {
                    "completion": {"disableSnippets": False, "resolveEagerly": False, "ignorePatterns": []},
                    "diagnostics": {"enable": False, "didOpen": True, "didChange": False, "didSave": False},
                    "hover": {
                        "enable": False,
                    },
                },
            },
        }
        self.send_request(initialize_request)

    def send_request(self, request: dict) -> dict:
        request_id = request["id"]

        # Send the request
        self.websocket.send(json.dumps(request))

        return self.get_response(request_id, request)

    def send_notification(self, notification: dict) -> None:
        self.websocket.send(json.dumps(notification))

    def get_response(self, request_id: str, request: dict) -> dict:
        # Check the response cache first
        if request_id in self.unmatched_responses:
            return self.unmatched_responses.pop(request_id)

        retries = 0
        while retries <= self.connection_retries:
            try:
                response = self.websocket.recv()
                response = json.loads(response)

                if response.get("method") == "window/logMessage":
                    self.log(response)

                response_id = response.get("id")

                if response_id == request_id:
                    return response
                else:
                    self.unmatched_responses[response_id] = response
            except ConnectionClosedError:
                retries += 1
                logger.info(f"Connection lost. Retrying ({retries}/{self.connection_retries})...")
                self.connect()
                self.websocket.send(json.dumps(request))
                if retries > self.connection_retries:
                    raise ConnectionClosedError("Failed to reconnect after maximum retries.")

    def get_document_symbols(self, document_uri: str) -> dict:
        document_symbol_request = {
            "jsonrpc": "2.0",
            "id": self.id,
            "method": "textDocument/documentSymbol",
            "params": {"textDocument": {"uri": document_uri}},
        }
        return self.send_request(document_symbol_request).get("result")

    def get_definition(self, document_uri: str, position: dict) -> dict:
        definition_request = {
            "jsonrpc": "2.0",
            "id": self.id,
            "method": "textDocument/definition",
            "params": {
                "textDocument": {"uri": document_uri},
                "position": position,
            },
        }

        result = self.send_request(definition_request).get("result")
        if result:
            return result[0]
        return None

    def get_declaration(self, document_uri: str, position: dict) -> dict:
        declaration_request = {
            "jsonrpc": "2.0",
            "id": self.id,
            "method": "textDocument/declaration",
            "params": {
                "textDocument": {"uri": document_uri},
                "position": position,
            },
        }
        result = self.send_request(declaration_request).get("result")
        if result:
            return result[0]
        return None

    def get_references(self, document_uri: str, position: dict) -> dict:
        reference_request = {
            "jsonrpc": "2.0",
            "id": self.id,
            "method": "textDocument/references",
            "params": {
                "textDocument": {"uri": document_uri},
                "position": position,
                "context": {"includeDeclaration": False},
                "workDoneToken": 1,
            },
        }
        return self.send_request(reference_request).get("result")

    def get_selection_range(self, document_uri: str, position: dict) -> dict:
        selection_range_request = {
            "jsonrpc": "2.0",
            "id": self.id,
            "method": "textDocument/selectionRange",
            "params": {
                "textDocument": {"uri": document_uri},
                "position": position,
            },
        }
        return self.send_request(selection_range_request).get("result")

    def get_document_link(self, document_uri: str) -> dict:
        document_link_request = {
            "jsonrpc": "2.0",
            "id": self.id,
            "method": "textDocument/documentLink",
            "params": {"textDocument": {"uri": document_uri}},
        }
        return self.send_request(document_link_request).get("result")

    def did_open(self, document_uri: str, text: str, extension: str) -> None:
        language_id = LANGUAGES_ID_MAP.get(extension, "javascript")
        did_open_notification = {
            "jsonrpc": "2.0",
            "id": 400,
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": document_uri,
                    "languageId": language_id,
                    "version": 1,
                    "text": text,
                },
            },
        }
        self.send_notification(did_open_notification)

    def shutdown_exit_close(self) -> None:
        try:
            self.shutdown()
            self.exit()
            self.close()
        except ConnectionClosedError:
            pass
        except Exception as e:
            logger.info(f"Error closing connection {e}")

    def shutdown(self) -> None:
        shutdown_request = {
            "jsonrpc": "2.0",
            "id": self.id,
            "method": "shutdown",
            "params": None,
        }
        self.send_request(shutdown_request)

    def exit(self) -> None:
        exit_request = {"jsonrpc": "2.0", "method": "exit"}
        self.websocket.send(json.dumps(exit_request))

    def close(self) -> None:
        self.websocket.close()

    def map_reference(self, reference: dict) -> dict:
        return {
            "uri": reference["uri"],
            "range": reference["range"],
        }

    def log(self, message: dict) -> None:
        if self.log:
            self.pretty_print(message)

    def pretty_print(self, message: dict) -> None:
        ## print formatted json
        Logger.log(json.dumps(message, indent=2))
