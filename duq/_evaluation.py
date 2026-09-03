import asyncio
import json
import time
from typing import AsyncIterator, Awaitable

import bs4
import requests

from duq._syntax import parse
from duq._types import Expr, Value


def evaluate_expr(expr: Expr, inp: Value) -> Value:
    if expr is None or isinstance(expr, (int, float, str, bool)):
        return expr

    proc_name = expr["name"]
    raw_args = expr["args"]

    ## Macros

    # basic
    if proc_name == "do":
        return evaluate_chain(raw_args, inp)

    # list
    elif proc_name == "map":
        assert type(inp) is list
        result = []
        for item in inp:
            result.append(evaluate_chain(raw_args, item))
        return result
    elif proc_name == "filter":
        assert type(inp) is list
        result = []
        for item in inp:
            cond = evaluate_chain(raw_args, item)
            assert type(cond) is bool
            if cond:
                result.append(item)
        return result
    elif proc_name == "groupBy":
        assert type(inp) is list
        result = {}
        for item in inp:
            key = evaluate_chain(raw_args, item)
            assert type(key) is str
            result.setdefault(key, []).append(item)
        return result
    elif proc_name == "keyBy":
        assert type(inp) is list
        result = {}
        for item in inp:
            key = evaluate_chain(raw_args, item)
            assert type(key) is str
            assert key not in result
            result[key] = item
        return result

    # record
    elif proc_name == "mapValues":
        assert type(inp) is dict
        return {key: evaluate_chain(raw_args, value) for key, value in inp.items()}

    # future
    elif proc_name == "future.map":
        assert isinstance(inp, Awaitable)

        async def map_future() -> Value:
            value = await inp
            return evaluate_chain(raw_args, value)

        return map_future()

    # stream
    elif proc_name == "stream.map":
        assert isinstance(inp, AsyncIterator)

        async def map_stream() -> AsyncIterator[Value]:
            async for item in inp:
                yield evaluate_chain(raw_args, item)

        return map_stream()
    elif proc_name == "stream.filter":
        assert isinstance(inp, AsyncIterator)

        async def filter_stream() -> AsyncIterator[Value]:
            async for item in inp:
                cond = evaluate_chain(raw_args, item)
                assert type(cond) is bool
                if cond:
                    yield item

        return filter_stream()
    elif proc_name == "stream.first":
        assert isinstance(inp, AsyncIterator)

        async def stream_first() -> Value:
            async for item in inp:
                return item

        return stream_first()

    ## Functions

    args = [evaluate_expr(arg, inp) for arg in raw_args]

    # basic
    if proc_name == "id":
        assert len(args) == 0
        return inp
    elif proc_name == "eq":
        assert len(args) == 1
        assert type(args[0]) is type(inp)
        assert type(inp) in [int, str]
        return inp == args[0]

    # number
    elif proc_name == "float":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) is str or type(arg) is int or type(arg) is float
        return float(arg)
    elif proc_name == "int":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) is int or type(arg) is str
        return int(arg, base=0) if type(arg) is str else arg
    elif proc_name == "add":
        assert len(args) == 1
        assert type(args[0]) is int or type(args[0]) is float
        assert type(inp) is int or type(inp) is float
        return inp + args[0]
    elif proc_name == "sub":
        assert len(args) == 1
        assert type(args[0]) is int or type(args[0]) is float
        assert type(inp) is int or type(inp) is float
        return inp - args[0]

    # str
    elif proc_name == "str":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) in [str, int, float, bool]
        if type(arg) is bool:
            return str(arg).lower()
        return str(arg)
    elif proc_name == "trim":
        assert len(args) == 0
        assert type(inp) is str
        return inp.strip()
    elif proc_name == "rmPrefix":
        assert len(args) == 1
        assert type(args[0]) is str
        assert type(inp) is str
        return inp.removeprefix(args[0])
    elif proc_name == "rmSuffix":
        assert len(args) == 1
        assert type(args[0]) is str
        assert type(inp) is str
        return inp.removesuffix(args[0])
    elif proc_name == "join":
        assert len(args) == 0 or len(args) == 1
        sep = "" if len(args) == 0 else args[0]
        assert type(sep) is str
        assert type(inp) is list
        for item in inp:
            assert type(item) is str
        return sep.join(inp)  # type: ignore

    # list
    elif proc_name == "list":
        return args
    elif proc_name == "index":
        assert len(args) == 1
        index = args[0]
        assert type(index) is int
        assert type(inp) is list
        assert index >= -len(inp) and index < len(inp)
        return inp[index]
    elif proc_name == "slice":
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
    elif proc_name == "flatten":
        assert len(args) == 0
        assert type(inp) is list
        result = []
        for item in inp:
            assert type(item) is list
            result += item
        return result
    elif proc_name == "range":
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
    elif proc_name == "count":
        assert len(args) == 0
        assert type(inp) is list
        return len(inp)
    elif proc_name == "sum":
        assert len(args) == 0
        assert type(inp) is list
        total = 0
        for item in inp:
            assert type(item) is int or type(item) is float
            total += item
        return total
    elif proc_name == "mean":
        assert len(args) == 0
        assert type(inp) is list
        if len(inp) == 0:
            return 0.0
        total = 0
        for item in inp:
            assert type(item) is int or type(item) is float
            total += item
        return total / len(inp)

    # record
    elif proc_name == "field":
        assert len(args) == 1
        assert type(args[0]) is str
        assert type(inp) is dict
        assert args[0] in inp
        return inp[args[0]]

    # file
    elif proc_name == "file.read":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) is str
        with open(arg, "r") as f:
            return f.read()

    # http
    elif proc_name == "http.fetch":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) is str
        response = requests.get(
            arg,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
            },
        )
        if not response.ok:
            raise Exception(f"request error: {arg} -> {response.status_code}")
        return response.text

    # stream
    elif proc_name == "stream.every":
        assert len(args) == 1
        arg = args[0]
        assert type(arg) is int or type(arg) is float

        async def every(secs: float) -> AsyncIterator[None]:
            while True:
                start = time.time()
                yield None
                duration = max(start + secs - time.time(), 0)
                await asyncio.sleep(duration)

        return every(arg)

    # json
    elif proc_name == "json":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) is str
        return json.loads(arg)
    elif proc_name == "json.pretty":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        return json.dumps(arg, indent=2)

    # html
    elif proc_name == "html":
        assert len(args) == 0
        assert type(inp) is str
        return bs4.BeautifulSoup(inp, "html.parser")
    elif proc_name == "html.select":
        assert len(args) == 1
        assert type(args[0]) is str
        assert isinstance(inp, bs4.Tag)
        return list(inp.select(args[0]))
    elif proc_name == "html.text":
        assert len(args) == 0
        assert isinstance(inp, bs4.Tag)
        return inp.text

    raise Exception(f"unknown procedure: {proc_name}")


def evaluate_chain(exprs: list[Expr], inp: Value) -> Value:
    for expr in exprs:
        inp = evaluate_expr(expr, inp)
    return inp


def evaluate(source: str, inp: Value = None) -> Value:
    exprs = parse(source)
    return evaluate_chain(exprs, inp)
