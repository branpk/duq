import asyncio
from dataclasses import dataclass
from datetime import datetime
import json
import time
from typing import Any, AsyncIterator, Awaitable, Coroutine, Iterable

import bs4
import httpx

from duq._syntax import parse, Expr


@dataclass
class Hinted[T]:
    hint: str
    value: T


type Value = (
    None
    | int
    | float
    | str
    | bool
    | list[Value]
    | dict[str, Value]
    | Awaitable[Value]
    | AsyncIterator[Value]
    | Hinted[Value]
    | bs4.Tag
)


def evaluate_expr(expr: Expr, inp: Value) -> Value:
    if expr.type == "literal":
        return expr.value

    while isinstance(inp, Hinted):
        inp = inp.value

    op_name = expr.name.text
    raw_args: tuple[Expr, ...] = expr.arg_list.exprs if expr.arg_list else ()

    if op_name == "{":
        if type(inp) is list:
            op_name = "map"
        elif type(inp) is dict:
            op_name = "mapValues"
        elif isinstance(inp, Awaitable):
            op_name = "future.map"
        elif isinstance(inp, AsyncIterator):
            op_name = "stream.map"
        else:
            raise Exception(f"invalid type for `{{`: {type(inp)}")

    ## Macros

    # basic
    if op_name == "do":
        return evaluate_chain(raw_args, inp)

    # list
    elif op_name == "map":
        assert type(inp) is list
        result = []
        for item in inp:
            result.append(evaluate_chain(raw_args, item))
        return result
    elif op_name == "filter":
        assert type(inp) is list
        result = []
        for item in inp:
            cond = evaluate_chain(raw_args, item)
            assert type(cond) is bool
            if cond:
                result.append(item)
        return result
    elif op_name == "groupBy":
        assert type(inp) is list
        result = {}
        for item in inp:
            key = evaluate_chain(raw_args, item)
            assert type(key) is str
            result.setdefault(key, []).append(item)
        return result
    elif op_name == "keyBy":
        assert type(inp) is list
        result = {}
        for item in inp:
            key = evaluate_chain(raw_args, item)
            assert type(key) is str
            assert key not in result
            result[key] = item
        return result

    # record
    elif op_name == "mapValues":
        assert type(inp) is dict
        return {key: evaluate_chain(raw_args, value) for key, value in inp.items()}

    # future
    elif op_name == "future.map":
        assert isinstance(inp, Awaitable)

        async def map_future() -> Value:
            value = await inp
            return evaluate_chain(raw_args, value)

        return map_future()

    # stream
    elif op_name == "stream.map":
        assert isinstance(inp, AsyncIterator)

        async def map_stream() -> AsyncIterator[Value]:
            async for item in inp:
                yield evaluate_chain(raw_args, item)

        return map_stream()
    elif op_name == "stream.filter":
        assert isinstance(inp, AsyncIterator)

        async def filter_stream() -> AsyncIterator[Value]:
            async for item in inp:
                cond = evaluate_chain(raw_args, item)
                assert type(cond) is bool
                if cond:
                    yield item

        return filter_stream()
    elif op_name == "stream.first":
        assert isinstance(inp, AsyncIterator)

        async def stream_first() -> Value:
            async for item in inp:
                return item

        return stream_first()
    elif op_name == "stream.accum":
        assert isinstance(inp, AsyncIterator)
        assert len(raw_args) == 2
        init = evaluate_expr(raw_args[0], None)

        async def stream_accum() -> AsyncIterator[Value]:
            current = init
            yield current
            async for item in inp:
                current = evaluate_expr(raw_args[1], [current, item])
                yield current

        return stream_accum()

    ## Functions

    args = []
    for arg in raw_args:
        arg = evaluate_expr(arg, inp)
        while isinstance(arg, Hinted):
            arg = arg.value
        args.append(arg)

    # basic
    if op_name == "id":
        assert len(args) == 0
        return inp
    elif op_name == "eq":
        assert len(args) == 1
        value_types = [int, float, str, bool, list, dict]
        assert args[0] is None or type(args[0]) in value_types
        assert inp is None or type(inp) in value_types
        return inp == args[0]
    elif op_name == "time.now":
        assert len(args) == 0
        return datetime.now().isoformat(timespec="milliseconds") + "Z"
    elif op_name == "hint":
        assert len(args) == 1
        assert type(args[0]) is str
        return Hinted(args[0], inp)
    elif op_name == "tableToRecords":
        assert len(args) == 0
        assert type(inp) is list
        assert len(inp) > 0
        header_row = inp[0]
        assert type(header_row) is list
        assert all(type(cell) is str for cell in header_row)
        rows = inp[1:]
        result = []
        for row in rows:
            assert type(row) is list
            record = {}
            for i, header in enumerate(header_row):
                record[header] = None if i >= len(row) else row[i]
            result.append(record)
        return result
    elif op_name == "blank":
        assert len(args) == 0
        return inp is None or (type(inp) is str and inp.strip() == "")

    # bool
    elif op_name == "not":
        assert len(args) == 0
        assert type(inp) is bool
        return not inp

    # number
    elif op_name == "float":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) is str or type(arg) is int or type(arg) is float
        return float(arg)
    elif op_name == "int":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) is int or type(arg) is str
        return int(arg, base=0) if type(arg) is str else arg
    elif op_name == "add":
        assert len(args) == 1
        assert type(args[0]) is int or type(args[0]) is float
        assert type(inp) is int or type(inp) is float
        return inp + args[0]
    elif op_name == "sub":
        assert len(args) == 1
        assert type(args[0]) is int or type(args[0]) is float
        assert type(inp) is int or type(inp) is float
        return inp - args[0]

    # str
    elif op_name == "str":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) in [str, int, float, bool]
        if type(arg) is bool:
            return str(arg).lower()
        return str(arg)
    elif op_name == "trim":
        assert len(args) == 0
        assert type(inp) is str
        return inp.strip()
    elif op_name == "rmPrefix":
        assert len(args) == 1
        assert type(args[0]) is str
        assert type(inp) is str
        return inp.removeprefix(args[0])
    elif op_name == "rmSuffix":
        assert len(args) == 1
        assert type(args[0]) is str
        assert type(inp) is str
        return inp.removesuffix(args[0])
    elif op_name == "join":
        assert len(args) == 0 or len(args) == 1
        sep = "" if len(args) == 0 else args[0]
        assert type(sep) is str
        assert type(inp) is list
        for item in inp:
            assert type(item) is str
        return sep.join(inp)  # type: ignore

    # list
    elif op_name == "list":
        return args
    elif op_name == "index":
        assert len(args) == 1
        index = args[0]
        assert type(index) is int
        assert type(inp) is list
        assert index >= -len(inp) and index < len(inp)
        return inp[index]
    elif op_name == "slice":
        assert len(args) == 1 or len(args) == 2
        assert type(inp) is list
        if len(args) == 1:
            start = args[0]
            end = len(inp)
        else:
            start = args[0]
            end = args[1]
        assert type(start) is int
        assert type(end) is int
        start = max(start, 0)
        end = min(end, len(inp))
        if start >= end:
            return []
        else:
            return inp[start:end]
    elif op_name == "flatten":
        assert len(args) == 0
        assert type(inp) is list
        result = []
        for item in inp:
            assert type(item) is list
            result += item
        return result
    elif op_name == "range":
        assert len(args) == 1 or len(args) == 2
        if len(args) == 1:
            start = 0
            end = args[0]
        else:
            start = args[0]
            end = args[1]
        assert type(start) is int
        assert type(end) is int
        return list(range(start, end))
    elif op_name == "count":
        assert len(args) == 0
        assert type(inp) is list
        return len(inp)
    elif op_name == "sum":
        assert len(args) == 0
        assert type(inp) is list
        total = 0
        for item in inp:
            assert type(item) is int or type(item) is float
            total += item
        return total
    elif op_name == "mean":
        assert len(args) == 0
        assert type(inp) is list
        if len(inp) == 0:
            return 0.0
        total = 0
        for item in inp:
            assert type(item) is int or type(item) is float
            total += item
        return total / len(inp)
    elif op_name == "list.stream":
        assert len(args) == 0
        assert type(inp) is list

        async def list_stream() -> AsyncIterator[Value]:
            for item in inp:
                yield item

        return list_stream()

    # record
    elif op_name == "field":
        assert len(args) == 1
        assert type(args[0]) is str
        assert type(inp) is dict
        assert args[0] in inp
        return inp[args[0]]
    elif op_name.startswith("."):
        assert len(args) == 0
        key = op_name[1:]
        assert type(inp) is dict
        assert key in inp
        return inp[key]

    # file
    elif op_name == "file.read":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) is str
        with open(arg, "r") as f:
            return f.read()

    # http
    elif op_name == "http.fetch":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) is str

        async def fetch_task():
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    arg,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
                    },
                )
                if response.status_code != 200:
                    raise Exception(f"request error: {arg} -> {response.status_code}")
            return response.text

        return fetch_task()

    # future
    elif op_name == "future.sleep":
        assert len(args) == 1
        arg = args[0]
        assert type(arg) is int or type(arg) is float
        assert arg >= 0
        return asyncio.sleep(arg)
    elif op_name == "future.all":
        assert len(args) == 0
        assert type(inp) is list
        assert all(isinstance(item, Awaitable) for item in inp)

        async def all_task() -> list[Value]:
            return await asyncio.gather(*inp)  # type: ignore

        return all_task()

    # stream
    elif op_name == "stream.interval":
        assert len(args) == 1
        arg = args[0]
        assert type(arg) is int or type(arg) is float
        assert arg >= 0

        async def interval(secs: float) -> AsyncIterator[Value]:
            prev = time.time()
            while True:
                duration = max(prev + secs - time.time(), 0)
                await asyncio.sleep(duration)
                yield None
                prev = time.time()

        return interval(arg)
    elif op_name == "stream.limit":
        assert len(args) == 1
        arg = args[0]
        assert type(arg) is int
        assert arg >= 0
        assert isinstance(inp, AsyncIterator)

        async def limit(n: int) -> AsyncIterator[Value]:
            if n > 0:
                async for item in inp:
                    yield item
                    n -= 1
                    if n <= 0:
                        break

        return limit(arg)

    # json
    elif op_name == "json":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) is str
        return json.loads(arg)
    elif op_name == "json.pretty":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        return json.dumps(arg, indent=2)

    # html
    elif op_name == "html":
        assert len(args) == 0
        assert type(inp) is str
        return bs4.BeautifulSoup(inp, "html.parser")
    elif op_name == "html.select":
        assert len(args) == 1
        assert type(args[0]) is str
        assert isinstance(inp, bs4.Tag)
        return list(inp.select(args[0]))
    elif op_name == "html.text":
        assert len(args) == 0
        assert isinstance(inp, bs4.Tag)
        return inp.text

    raise Exception(f"unknown operation: {op_name}")


def evaluate_chain(exprs: Iterable[Expr], inp: Value) -> Value:
    for expr in exprs:
        inp = evaluate_expr(expr, inp)
    return inp


def evaluate(source: str, inp: Value = None) -> Value:
    expr_list = parse(source)
    return evaluate_chain(expr_list.exprs, inp)
