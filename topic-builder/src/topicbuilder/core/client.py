import asyncio
import json
import os
from pathlib import Path
from typing import Any, TypedDict, TypeVar

import yaml
from dotenv import load_dotenv
from loguru import logger
from openai import AsyncAzureOpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletion
from pydantic import BaseModel, ValidationError
from tqdm.asyncio import tqdm_asyncio

BACKENDS = {
    "default": AsyncOpenAI,
    "azure": AsyncAzureOpenAI,
}


class ChatMessage(TypedDict):
    role: str
    content: str


class LLMClient:
    """
    Base class for OpenAI-compatible endpoint clients.
    """

    def __init__(
        self,
        backend: str,
        model: str,
        pool_size: int,
        api_key_env_var: str | None,
        endpoint_args: dict[str, Any],
    ) -> None:
        """
        Initialize the base openai client with a model name and concurrency pool.
        """
        self.model = model
        self.client = self.init_client(backend, api_key_env_var, endpoint_args)
        self.pool_size = pool_size
        self._semaphore: asyncio.Semaphore | None = None
        self._semaphore_loop: asyncio.AbstractEventLoop | None = None

    @classmethod
    def from_config(cls, config_path: str | Path) -> "LLMClient":
        """
        Create an instance of LLMClient from a config path.
        """
        with Path(config_path).resolve().open(encoding="utf-8") as f:
            return cls(**yaml.safe_load(f))

    @staticmethod
    def init_client(backend: str, api_key_env_var: str | None, endpoint_args: dict[str, Any]) -> AsyncOpenAI:
        """
        Init LLM client.
        """
        load_dotenv()
        api_key = os.environ[api_key_env_var] if api_key_env_var else "EMPTY"
        if (backend_class := BACKENDS.get(backend)) is None:
            raise ValueError(f"Missing 'backend' from the list of possible backends: {BACKENDS.keys()}")
        return backend_class(api_key=api_key, **endpoint_args)

    # @backoff.on_exception(backoff.expo, (Exception, TimeoutException, APITimeoutError), max_tries=5)
    async def async_query(self, messages: list[ChatMessage], **kwargs: Any) -> ChatCompletion:
        """
        Run an asynchronous chat completion query and return the raw response.
        """
        return await self.client.chat.completions.create(model=self.model, messages=messages, **kwargs)

    def _get_semaphore(self) -> asyncio.Semaphore:
        """
        Return a semaphore bound to the currently running event loop, recreating it
        whenever the loop has changed (e.g. across successive `asyncio.run` calls).
        """
        loop = asyncio.get_running_loop()
        if self._semaphore is None or self._semaphore_loop is not loop:
            self._semaphore = asyncio.Semaphore(self.pool_size)
            self._semaphore_loop = loop
        return self._semaphore

    async def async_run_one(self, messages: list[ChatMessage], **kwargs: Any) -> ChatCompletion:
        """
        Run the async query inside the semaphore for concurrency control.
        """
        async with self._get_semaphore():
            return await self.async_query(messages, **kwargs)

    async def async_run_all(self, inputs: list[list[ChatMessage]], **kwargs: Any) -> list[ChatCompletion]:
        """
        Run async_call concurrently for each message list in `batch` and return results in order.
        """
        return await tqdm_asyncio.gather(*[self.async_run_one(messages, **kwargs) for messages in inputs])

    def __call__(self, inputs: list[list[ChatMessage]], **kwargs: Any) -> list[ChatCompletion]:
        """
        Synchronously run a batch of queries and return one ChatCompletion per input.
        """
        return asyncio.run(self.async_run_all(inputs, **kwargs))


T = TypeVar("T", bound=BaseModel)


def parse_tool_arguments(response: ChatCompletion, cls: type[T]) -> T | None:
    """
    Extract and validate the forced tool-call arguments against `cls`. Returns None on failure.
    """
    try:
        return cls.model_validate(extract_tool_arguments(response))
    except ValidationError:
        logger.warning("Tool arguments failed validation for {}", cls.__name__)
        return None


def extract_tool_arguments(response: ChatCompletion) -> dict:
    """
    Pull and JSON-parse the arguments from the forced tool call in the response.
    """
    if len(response.choices) == 0:
        logger.warning("response has empty list of choices")
        return {}

    if (tcs := response.choices[0].message.tool_calls) is None or len(tcs) == 0:
        logger.warning("response has empty list of tool calls")
        return {}

    return json.loads(tcs[0].function.arguments)
