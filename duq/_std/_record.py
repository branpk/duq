from typing import Any

from duq._evaluation import Context
from duq._syntax import Expr
from duq._type_check import type_check_value


def op_map(ctx: Context, input: dict[str, Any], *args: Expr) -> dict[str, Any]:
    return {key: ctx.evaluate_chain(args, value) for key, value in input.items()}


def op_field(input: dict[str, Any], field: str) -> Any:
    if field not in input:
        raise Exception(f"no such field: `{field}`")
    return input[field]


def op_items(input: dict[str, Any]) -> list[list[Any]]:
    return list(map(list, input.items()))


def op_mapField(
    ctx: Context, input: dict[str, Any], field: Expr, *args: Expr
) -> dict[str, Any]:
    field_name = ctx.evaluate_expr(field, input)
    type_check_value(field_name, str)
    if field_name not in input:
        raise Exception(f"no such field: `{field_name}`")
    result = dict(input)
    result[field_name] = ctx.evaluate_chain(args, input[field_name])
    return result


def op_mapFieldOpt(
    ctx: Context, input: dict[str, Any], field: Expr, *args: Expr
) -> dict[str, Any]:
    field_name = ctx.evaluate_expr(field, input)
    type_check_value(field_name, str)
    result = dict(input)
    result[field_name] = ctx.evaluate_chain(args, input.get(field_name))
    return result


op_definitions = {
    "std.record.map": op_map,
    "std.record.field": op_field,
    "std.record.items": op_items,
    "std.record.mapField": op_mapField,
    "std.record.mapFieldOpt": op_mapFieldOpt,
}
