import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from duq._evaluation_v2 import evaluate_chain
from duq._syntax import Expr
from duq._util import IntoAwaitable


def op_sleep(seconds: float) -> IntoAwaitable[None]:
    return IntoAwaitable(lambda: asyncio.sleep(seconds))


def op_map(input: IntoAwaitable[Any], *args: Expr) -> IntoAwaitable[Any]:
    async def task():
        value = await input.create()
        return evaluate_chain(args, value)

    return IntoAwaitable(task)


def op_all(input: list[IntoAwaitable[Any]]) -> IntoAwaitable[list[Any]]:
    async def task():
        children = [child.create() for child in input]
        return await asyncio.gather(*children)

    return IntoAwaitable(task)


op_definitions = {
    "std.future.sleep": op_sleep,
    "std.future.map": op_map,
    "std.future.all": op_all,
}
