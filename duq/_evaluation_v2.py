from dataclasses import dataclass
from typing import Any, Iterable

from duq._context import global_context
from duq._syntax import Expr, parse


@dataclass
class Hinted[T]:
    hint: str
    value: T


def evaluate_expr(expr: Expr, input: Any) -> Any:
    if expr.type == "literal":
        return expr.value

    while isinstance(input, Hinted):
        input = input.value

    ctx = global_context()

    args = []
    if expr.name.text.startswith("."):
        op = ctx.resolve_op("std.record.field", input)
        args.append(expr.name.text.removeprefix("."))
    elif expr.name.text == "{":
        op = ctx.resolve_op("map", input)
    else:
        op = ctx.resolve_op(expr.name.text, input)

    arg_exprs = () if expr.arg_list is None else expr.arg_list.exprs
    if op.signature.is_macro:
        args += arg_exprs
    else:
        for arg_expr in arg_exprs:
            arg = evaluate_expr(arg_expr, input)
            while isinstance(arg, Hinted):
                arg = arg.value
            args.append(arg)

    args = tuple(args)
    op.signature.type_check_inputs(input, args)

    call_args = op.signature.get_call_args(input, args)
    return op.op_func(*call_args)


def evaluate_chain(exprs: Iterable[Expr], input: Any) -> Any:
    for expr in exprs:
        input = evaluate_expr(expr, input)
    return input


def evaluate(source: str, input: Any = None) -> Any:
    expr_list = parse(source)
    return evaluate_chain(expr_list.exprs, input)
