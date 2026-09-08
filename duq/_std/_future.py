import asyncio
from typing import Any

from duq._evaluation import DuqContext
from duq._syntax import Expr
from duq._util import DuqFuture


def op_sleep(seconds: int | float) -> DuqFuture[None]:
    return DuqFuture(lambda: asyncio.sleep(seconds))


def op_map(ctx: DuqContext, input: DuqFuture[Any], body: Expr) -> DuqFuture[Any]:
    async def task():
        value = await input.create()
        return ctx.evaluate(body, value)

    return DuqFuture(task)


def op_all(input: list[DuqFuture[Any]]) -> DuqFuture[list[Any]]:
    async def task():
        children = [child.create() for child in input]
        return await asyncio.gather(*children)

    return DuqFuture(task)


op_definitions = {
    "std.future.sleep": op_sleep,
    "std.future.map": op_map,
    "std.future.all": op_all,
}
