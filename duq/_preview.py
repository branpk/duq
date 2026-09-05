from dataclasses import dataclass
import dataclasses
import json

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


class Preview:
    def __init__(self) -> None:
        self.source = ""
        self.cursor_position = 0

    def set_source(self, source: str) -> None:
        self.source = source

    def set_cursor_position(self, cursor_position: int) -> None:
        self.cursor_position = cursor_position

    def get_output(self) -> str:
        try:
            expr_list = parse(self.source)
            truncated = truncate_expr_list(expr_list, self.cursor_position)
            result = evaluate_chain(truncated.exprs, None)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error: {e}"
