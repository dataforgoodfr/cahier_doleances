"""
Shared fixtures for integration tests: mock vLLM HTTP server.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

MOCK_DISCOVER_TOPICS_RESPONSE: dict = {
    "id": "chatcmpl-mock-build",
    "object": "chat.completion",
    "model": "mock-model",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_mock_build",
                        "type": "function",
                        "function": {
                            "name": "record_new_topics",
                            "arguments": json.dumps(
                                {
                                    "topics": [
                                        {
                                            "name": "Soil Composition",
                                            "description": (
                                                "The mineral and organic components that make up"
                                                " soil and support water retention and plant growth."
                                            ),
                                        },
                                    ]
                                }
                            ),
                        },
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }
    ],
    "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
}

MOCK_CLEAN_RESPONSE: dict = {
    "id": "chatcmpl-mock-clean",
    "object": "chat.completion",
    "model": "mock-model",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_mock_clean",
                        "type": "function",
                        "function": {
                            "name": "record_topic_cleanup",
                            "arguments": json.dumps(
                                {
                                    "merges": [
                                        {
                                            "target": "Water Cycle",
                                            "sources": ["Hydrological Cycle"],
                                        }
                                    ],
                                    "parents_added": [
                                        {
                                            "parent": "Earth Sciences",
                                            "children": [
                                                "Water Cycle",
                                                "Photosynthesis",
                                            ],
                                        }
                                    ],
                                }
                            ),
                        },
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }
    ],
    "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
}

MOCK_FIND_RESPONSE: dict = {
    "id": "chatcmpl-mock-find",
    "object": "chat.completion",
    "model": "mock-model",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_mock_find",
                        "type": "function",
                        "function": {
                            "name": "record_labeled_topics",
                            "arguments": json.dumps(
                                {
                                    "topics": [
                                        {
                                            "name": "Water Cycle",
                                            "rationale": (
                                                "The text describes how water moves between"
                                                " atmosphere, surface, and groundwater."
                                            ),
                                            "extract": (
                                                "The water cycle describes the continuous movement"
                                                " of water on, above, and below Earth's surface."
                                            ),
                                        },
                                        {
                                            "name": "Photosynthesis",
                                            "rationale": (
                                                "The text explains how plants use chlorophyll"
                                                " to convert light into chemical energy."
                                            ),
                                            "extract": (
                                                "Plants convert sunlight, carbon dioxide, and water"
                                                " into glucose and oxygen through photosynthesis."
                                            ),
                                        },
                                    ]
                                }
                            ),
                        },
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }
    ],
    "usage": {"prompt_tokens": 20, "completion_tokens": 20, "total_tokens": 40},
}

MOCK_MERGE_CANDIDATES_RESPONSE: dict = {
    "id": "chatcmpl-mock-merge-candidates",
    "object": "chat.completion",
    "model": "mock-model",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_mock_merge_candidates",
                        "type": "function",
                        "function": {
                            "name": "propose_merge_candidates",
                            "arguments": json.dumps(
                                {
                                    "groups": [
                                        {"names": ["Water Cycle", "Hydrological Cycle"]},
                                    ]
                                }
                            ),
                        },
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }
    ],
    "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
}

MOCK_MERGES_RESPONSE: dict = {
    "id": "chatcmpl-mock-merges",
    "object": "chat.completion",
    "model": "mock-model",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_mock_merges",
                        "type": "function",
                        "function": {
                            "name": "record_merges",
                            "arguments": json.dumps(
                                {
                                    "target": "Water Cycle",
                                    "sources": ["Hydrological Cycle"],
                                }
                            ),
                        },
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }
    ],
    "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
}

MOCK_PARENT_CANDIDATES_RESPONSE: dict = {
    "id": "chatcmpl-mock-parent-candidates",
    "object": "chat.completion",
    "model": "mock-model",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_mock_parent_candidates",
                        "type": "function",
                        "function": {
                            "name": "propose_parent_candidates",
                            "arguments": json.dumps(
                                {
                                    "candidates": [
                                        {
                                            "parent": "Earth Sciences",
                                            "children": ["Water Cycle", "Photosynthesis"],
                                        }
                                    ]
                                }
                            ),
                        },
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }
    ],
    "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
}

MOCK_PARENT_RESPONSE: dict = {
    "id": "chatcmpl-mock-parent",
    "object": "chat.completion",
    "model": "mock-model",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_mock_parent",
                        "type": "function",
                        "function": {
                            "name": "record_parent",
                            "arguments": json.dumps(
                                {
                                    "parent": "Earth Sciences",
                                    "description": (
                                        "Scientific disciplines studying Earth's physical structure,"
                                        " atmosphere, and natural processes."
                                    ),
                                    "children": ["Water Cycle", "Photosynthesis"],
                                }
                            ),
                        },
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }
    ],
    "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
}

_DISPATCH: dict[str, dict] = {
    "record_new_topics": MOCK_DISCOVER_TOPICS_RESPONSE,
    "record_topic_cleanup": MOCK_CLEAN_RESPONSE,
    "record_labeled_topics": MOCK_FIND_RESPONSE,
    "propose_merge_candidates": MOCK_MERGE_CANDIDATES_RESPONSE,
    "record_merges": MOCK_MERGES_RESPONSE,
    "propose_parent_candidates": MOCK_PARENT_CANDIDATES_RESPONSE,
    "record_parent": MOCK_PARENT_RESPONSE,
}


class _MockVllmHandler(BaseHTTPRequestHandler):
    """
    Minimal HTTP handler that dispatches a response based on the requested tool name.
    """

    def do_POST(self) -> None:  # noqa: N802
        """
        Return the appropriate mock payload based on the tool_choice function name.
        """
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        tool_name = body.get("tool_choice", {}).get("function", {}).get("name", "")
        payload = _DISPATCH.get(tool_name, MOCK_FIND_RESPONSE)
        encoded = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
        return None

    def log_message(self, *args) -> None:
        """
        Suppress default access log output.
        """
        return None


class MockVllmServer:
    """
    Lightweight HTTP server that mimics a vLLM OpenAI-compatible endpoint for tests.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        """
        Initialise the server; port=0 lets the OS assign a free port.
        """
        self._server = HTTPServer((host, port), _MockVllmHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        return None

    @property
    def base_url(self) -> str:
        """
        Return the base URL of the running server.
        """
        host, port = self._server.server_address
        return f"http://{host}:{port}/v1"

    def start(self) -> None:
        """
        Start serving requests in a background thread.
        """
        self._thread.start()
        return None

    def stop(self) -> None:
        """
        Shut the server down and wait for the thread to exit.
        """
        self._server.shutdown()
        self._thread.join()
        return None
