from typing import Any

from duq._evaluation import evaluate_chain
from duq._syntax import Expr
from duq._type_check import type_check_value


def op_map(input: list[Any], *args: Expr) -> list[Any]:
    result = []
    for element in input:
        result.append(evaluate_chain(args, element))
    return result


def op_filter(input: list[Any], *args: Expr) -> list[Any]:
    result = []
    for element in input:
        cond = evaluate_chain(args, element)
        type_check_value(cond, bool)
        if cond:
            result.append(element)
    return result


def op_groupBy(input: list[Any], *args: Expr) -> dict[str, Any]:
    result = {}
    for element in input:
        key = evaluate_chain(args, element)
        type_check_value(key, str)
        result.setdefault(key, []).append(element)
    return result


def op_keyBy(input: list[Any], *args: Expr) -> dict[str, Any]:
    result = {}
    for element in input:
        key = evaluate_chain(args, element)
        type_check_value(key, str)
        if key in result:
            raise Exception(f"duplicate key: {key}")
        result[key] = element
    return result


# TODO: tableToRecords


def op_list(*args: Any) -> list[Any]:
    return list(args)


op_definitions = {
    "list.map": op_map,
    "list.filter": op_filter,
    "list.groupBy": op_groupBy,
    "list.keyBy": op_keyBy,
    "list.list": op_list,
}
