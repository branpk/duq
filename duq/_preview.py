from dataclasses import dataclass
import dataclasses
import json
from typing import AsyncIterator, Awaitable, Callable

import bs4

from duq._evaluation import evaluate, Value, evaluate_chain
from duq._syntax import Expr, ExprList, OpExpr, get_token_value, parse


def truncate_expr(expr: Expr, cursor_position: int) -> Expr | None:
    if cursor_position <= expr.span[0]:
        return None
    if expr.type == "literal" or expr.arg_list is None:
        return expr
    arg_list = expr.arg_list
    if cursor_position >= arg_list.span[0] and cursor_position < arg_list.span[1]:
        arg_list = truncate_expr_list(arg_list, cursor_position)
    return OpExpr(type=expr.type, span=expr.span, name=expr.name, arg_list=arg_list)


def truncate_expr_list(expr_list: ExprList, cursor_position: int) -> ExprList:
    return ExprList(
        span=expr_list.span,
        exprs=tuple(
            expr1
            for expr in expr_list.exprs
            if (expr1 := truncate_expr(expr, cursor_position))
        ),
    )


def render_value(value: Value) -> str:
    if isinstance(value, Awaitable):
        return "<future>"
    elif isinstance(value, AsyncIterator):
        return "<stream>"
    elif isinstance(value, bs4.Tag):
        return "<html>"
    else:
        return json.dumps(value, indent=2)


class Preview:
    def __init__(
        self, set_output: Callable[[str], None], set_error: Callable[[str], None]
    ) -> None:
        self.source = ""
        self.cursor_position = 0
        self.current_value = None
        self.set_output = set_output
        self.set_error = set_error

        set_output("null")
        set_error("")

    def set_source(self, source: str) -> None:
        self.source = source
        self.refresh()

    def set_cursor_position(self, cursor_position: int) -> None:
        self.cursor_position = cursor_position
        self.refresh()

    def refresh(self) -> None:
        try:
            expr_list = parse(self.source)
            truncated = truncate_expr_list(expr_list, self.cursor_position)
            self.current_value = evaluate_chain(truncated.exprs, None)
            error = ""
        except Exception as e:
            error = f"Error: {e}"

        output = render_value(self.current_value)

        self.set_output(output)
        self.set_error(error)
