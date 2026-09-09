from typing import Any, AsyncIterator

from duq._evaluation import DuqContext, Hinted
from duq._syntax import Expr
from duq._type_check import type_check_value
from duq._util import DuqStream


def op_map(ctx: DuqContext, input: list[Any], body: Expr) -> list[Any]:
    result = []
    for element in input:
        result.append(ctx.evaluate(body, element))
    return result


def op_filter(ctx: DuqContext, input: list[Any], body: Expr) -> list[Any]:
    result = []
    for element in input:
        cond = ctx.evaluate(body, element)
        cond = type_check_value(cond, bool)
        if cond:
            result.append(element)
    return result


def op_groupBy(ctx: DuqContext, input: list[Any], body: Expr) -> dict[str, Any]:
    result = {}
    for element in input:
        key = ctx.evaluate(body, element)
        key = type_check_value(key, str)
        result.setdefault(key, []).append(element)
    return result


def op_keyBy(ctx: DuqContext, input: list[Any], body: Expr) -> dict[str, Any]:
    result = {}
    for element in input:
        key = ctx.evaluate(body, element)
        key = type_check_value(key, str)
        if key in result:
            raise Exception(f"duplicate key: {key}")
        result[key] = element
    return result


def op_list(*args: Any) -> list[Any]:
    return list(args)


def op_stream(input: list[Any]) -> DuqStream[Any]:
    async def stream() -> AsyncIterator[Any]:
        for element in input:
            yield element

    return DuqStream(stream)


def op_index(input: list[Any], index: int) -> Any:
    if index < -len(input) or index >= len(input):
        raise Exception(f"index out of range: {index}")
    return input[index]


def op_slice(input: list[Any], start: int, end: int | None = None) -> Any:
    if end is None:
        end = len(input)
    start = max(start, 0)
    end = min(end, len(input))
    return input[start:end] if start < end else []


def op_flatten(input: list[list[Any]]) -> list[Any]:
    result = []
    for element in input:
        result += element
    return result


def op_range(a: int, b: int | None = None) -> list[int]:
    if b is None:
        return list(range(a))
    else:
        return list(range(a, b))


def op_count(input: list[Any]) -> int:
    return len(input)


def op_sum(input: list[int | float]) -> int | float:
    result = 0
    for element in input:
        result += element
    return result


def op_mean(input: list[int | float]) -> float:
    if len(input) == 0:
        return 0.0
    total = op_sum(input)
    return total / len(input)


def op_sort(input: list[int | float]) -> list[int | float]:
    return sorted(input)


def op_distinct(input: list[Any]) -> list[Any]:
    result = []
    for element in input:
        if element not in result:
            result.append(element)
    return result


op_definitions = {
    "std.list.map": op_map,
    "std.list.filter": op_filter,
    "std.list.groupBy": op_groupBy,
    "std.list.keyBy": op_keyBy,
    "std.list.list": op_list,
    "std.list.stream": op_stream,
    "std.list.index": op_index,
    "std.list.slice": op_slice,
    "std.list.flatten": op_flatten,
    "std.list.range": op_range,
    "std.list.count": op_count,
    "std.list.sum": op_sum,
    "std.list.mean": op_mean,
    "std.list.sort": op_sort,
    "std.list.distinct": op_distinct,
}
