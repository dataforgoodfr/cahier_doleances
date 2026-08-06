import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import AsyncAzureOpenAI, AsyncOpenAI
from pydantic import BaseModel

from tests.unit.helpers import make_tool_response
from topicbuilder.core.client import LLMClient, extract_tool_arguments, parse_tool_arguments


class StubArgs(BaseModel):
    name: str


@pytest.mark.parametrize(
    "backend, expected_cls, endpoint_args",
    [
        ("default", AsyncOpenAI, {}),
        ("azure", AsyncAzureOpenAI, {"azure_endpoint": "https://example.com", "api_version": "2024-01-01"}),
    ],
)
def test_init_client_returns_expected_backend_class(backend, expected_cls, endpoint_args):
    client = LLMClient.init_client(backend, api_key_env_var=None, endpoint_args=endpoint_args)
    assert isinstance(client, expected_cls)


def test_init_client_raises_on_unknown_backend():
    with pytest.raises(ValueError):
        LLMClient.init_client("unknown", api_key_env_var=None, endpoint_args={})


def test_init_client_uses_placeholder_api_key_when_env_var_not_set():
    client = LLMClient.init_client("default", api_key_env_var=None, endpoint_args={})
    assert client.api_key == "EMPTY"


def test_init_client_reads_api_key_from_env_var(monkeypatch):
    monkeypatch.setenv("STUB_API_KEY", "secret")
    client = LLMClient.init_client("default", api_key_env_var="STUB_API_KEY", endpoint_args={})
    assert client.api_key == "secret"


def test_from_config_loads_real_yaml(tmp_path):
    config_path = tmp_path / "client.yaml"
    config_path.write_text("backend: default\nmodel: stub-model\npool_size: 3\napi_key_env_var:\nendpoint_args: {}\n")
    client = LLMClient.from_config(config_path)
    assert client.model == "stub-model"
    assert isinstance(client.semaphore, asyncio.Semaphore)


def _make_client_with_stub_backend(monkeypatch, pool_size: int = 2) -> LLMClient:
    monkeypatch.setattr(
        LLMClient, "init_client", staticmethod(lambda backend, api_key_env_var, endpoint_args: MagicMock())
    )
    return LLMClient(
        backend="default", model="stub-model", pool_size=pool_size, api_key_env_var=None, endpoint_args={}
    )


def test_call_returns_one_completion_per_input_in_order(monkeypatch):
    client = _make_client_with_stub_backend(monkeypatch)
    responses_by_content = {"a": SimpleNamespace(id="r1"), "b": SimpleNamespace(id="r2")}
    client.client.chat.completions.create = AsyncMock(
        side_effect=lambda model, messages, **kwargs: responses_by_content[messages[0]["content"]]
    )
    result = client([[{"role": "user", "content": "a"}], [{"role": "user", "content": "b"}]])
    assert result == [responses_by_content["a"], responses_by_content["b"]]


def test_call_forwards_kwargs_to_completions_create(monkeypatch):
    client = _make_client_with_stub_backend(monkeypatch)
    client.client.chat.completions.create = AsyncMock(return_value=SimpleNamespace(id="r"))
    client([[{"role": "user", "content": "a"}]], tool_choice={"type": "function", "function": {"name": "f"}})
    _, kwargs = client.client.chat.completions.create.call_args
    assert kwargs["tool_choice"] == {"type": "function", "function": {"name": "f"}}
    assert kwargs["model"] == "stub-model"


def test_extract_tool_arguments_parses_json_arguments():
    response = make_tool_response("some_tool", {"name": "x"})
    assert extract_tool_arguments(response) == {"name": "x"}


def test_extract_tool_arguments_returns_empty_dict_when_no_choices():
    response = SimpleNamespace(choices=[])
    assert extract_tool_arguments(response) == {}


def test_extract_tool_arguments_returns_empty_dict_when_tool_calls_is_none():
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=None))])
    assert extract_tool_arguments(response) == {}


def test_extract_tool_arguments_returns_empty_dict_when_tool_calls_is_empty():
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[]))])
    assert extract_tool_arguments(response) == {}


def test_parse_tool_arguments_returns_validated_model():
    response = make_tool_response("some_tool", {"name": "x"})
    assert parse_tool_arguments(response, StubArgs) == StubArgs(name="x")


def test_parse_tool_arguments_returns_none_on_validation_error():
    response = make_tool_response("some_tool", {"wrong_field": "x"})
    assert parse_tool_arguments(response, StubArgs) is None
