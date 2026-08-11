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
    "backend, endpoint_args, expected",
    [
        ("default", {}, AsyncOpenAI),
        ("azure", {"azure_endpoint": "https://example.com", "api_version": "2024-01-01"}, AsyncAzureOpenAI),
        ("unknown", {}, ValueError),
    ],
)
def test_init_client_returns_expected_backend_class_or_raises(backend, endpoint_args, expected):
    if expected is ValueError:
        with pytest.raises(ValueError):
            LLMClient.init_client(backend, api_key_env_var=None, endpoint_args=endpoint_args)
    else:
        client = LLMClient.init_client(backend, api_key_env_var=None, endpoint_args=endpoint_args)
        assert isinstance(client, expected)


@pytest.mark.parametrize(
    "api_key_env_var, env_value, expected_api_key",
    [
        (None, None, "EMPTY"),
        ("STUB_API_KEY", "secret", "secret"),
    ],
)
def test_init_client_resolves_api_key_from_env_var_or_placeholder(
    monkeypatch, api_key_env_var, env_value, expected_api_key
):
    if env_value is not None:
        monkeypatch.setenv(api_key_env_var, env_value)
    client = LLMClient.init_client("default", api_key_env_var=api_key_env_var, endpoint_args={})
    assert client.api_key == expected_api_key


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


def test_call_returns_completions_in_order_and_forwards_kwargs(monkeypatch):
    client = _make_client_with_stub_backend(monkeypatch)
    responses_by_content = {"a": SimpleNamespace(id="r1"), "b": SimpleNamespace(id="r2")}
    client.client.chat.completions.create = AsyncMock(
        side_effect=lambda model, messages, **kwargs: responses_by_content[messages[0]["content"]]
    )
    result = client(
        [[{"role": "user", "content": "a"}], [{"role": "user", "content": "b"}]],
        tool_choice={"type": "function", "function": {"name": "f"}},
    )
    assert result == [responses_by_content["a"], responses_by_content["b"]]
    _, kwargs = client.client.chat.completions.create.call_args
    assert kwargs["tool_choice"] == {"type": "function", "function": {"name": "f"}}
    assert kwargs["model"] == "stub-model"


def test_extract_tool_arguments_parses_json_arguments():
    response = make_tool_response("some_tool", {"name": "x"})
    assert extract_tool_arguments(response) == {"name": "x"}


@pytest.mark.parametrize(
    "choices",
    [
        [],
        [SimpleNamespace(message=SimpleNamespace(tool_calls=None))],
        [SimpleNamespace(message=SimpleNamespace(tool_calls=[]))],
    ],
)
def test_extract_tool_arguments_returns_empty_dict_when_no_tool_call(choices):
    response = SimpleNamespace(choices=choices)
    assert extract_tool_arguments(response) == {}


@pytest.mark.parametrize(
    "tool_args, expected",
    [
        ({"name": "x"}, StubArgs(name="x")),
        ({"wrong_field": "x"}, None),
    ],
)
def test_parse_tool_arguments_returns_validated_model_or_none(tool_args, expected):
    response = make_tool_response("some_tool", tool_args)
    assert parse_tool_arguments(response, StubArgs) == expected
