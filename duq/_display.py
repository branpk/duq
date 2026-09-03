import json
from typing import AsyncIterator, Awaitable, assert_never

import bs4

from duq._types import Value


async def print_value_async(value: Value) -> None:
    if isinstance(value, Awaitable):
        item = await value
        await print_value_async(item)
    elif isinstance(value, AsyncIterator):
        async for item in value:
            await print_value_async(item)
    else:
        print_value(value)


def print_value(value: Value) -> None:
    if isinstance(value, str):
        print(value)
    elif value is None or isinstance(value, (int, float, bool, list, dict)):
        print(json.dumps(value, indent=2))
    elif isinstance(value, Awaitable):
        raise Exception("use print_value_async for future")
    elif isinstance(value, AsyncIterator):
        raise Exception("use print_value_async for stream")
    elif isinstance(value, bs4.Tag):
        print(value.prettify())
    else:
        assert_never(value)
