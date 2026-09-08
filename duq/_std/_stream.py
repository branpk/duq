import asyncio
import time
from typing import Any, AsyncIterator

from duq._evaluation import Context
from duq._syntax import Expr
from duq._type_check import type_check_value
from duq._util import DuqFuture, DuqStream


def op_interval(seconds: int | float) -> DuqStream[None]:
    async def stream() -> AsyncIterator[None]:
        prev = time.time()
        while True:
            duration = max(prev + seconds - time.time(), 0)
            await asyncio.sleep(duration)
            yield None
            prev = time.time()

    return DuqStream(stream)


def op_map(ctx: Context, input: DuqStream[Any], *args: Expr) -> DuqStream[Any]:
    async def stream() -> AsyncIterator[Any]:
        async for item in input.create():
            yield ctx.evaluate_chain(args, item)

    return DuqStream(stream)


def op_filter(ctx: Context, input: DuqStream[Any], *args: Expr) -> DuqStream[Any]:
    async def stream() -> AsyncIterator[Any]:
        async for item in input.create():
            cond = ctx.evaluate_chain(args, item)
            type_check_value(cond, bool)
            if cond:
                yield item

    return DuqStream(stream)


def op_first(input: DuqStream[Any]) -> DuqFuture[Any]:
    async def task() -> Any:
        async for item in input.create():
            return item
        return None

    return DuqFuture(task)


def op_limit(input: DuqStream[Any], limit: int) -> DuqStream[Any]:
    async def stream() -> AsyncIterator[Any]:
        count = 0
        async for item in input.create():
            if count >= limit:
                break
            yield item
            count += 1

    return DuqStream(stream)


op_definitions = {
    "std.stream.interval": op_interval,
    "std.stream.map": op_map,
    "std.stream.filter": op_filter,
    "std.stream.first": op_first,
    "std.stream.limit": op_limit,
}
