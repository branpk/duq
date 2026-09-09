from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, assert_never

from duq._syntax import ChainExpr, Expr, OpExpr, parse
from duq._type_check import DuqTypeError, OpSignature, type_check_value


@dataclass
class OpInfo:
    name: str
    signature: OpSignature
    op_func: Callable


class DuqContext:
    def __init__(self) -> None:
        self.ops: dict[str, OpInfo] = {}
        self.cache: dict[str, Any] = {}
        self.cursor: int | None = None

    @staticmethod
    def create() -> DuqContext:
        import duq._std

        context = DuqContext()
        context.load_ops(duq._std.op_definitions)
        return context

    def load_op(self, name: str, op_func: Callable) -> None:
        if name in self.ops:
            raise Exception(f"redefined op: `{name}`")
        signature = OpSignature.of(name, op_func)
        self.ops[name] = OpInfo(name, signature, op_func)

    def load_ops(self, ops: dict[str, Callable]) -> None:
        for op_name, op_func in ops.items():
            self.load_op(op_name, op_func)

    def resolve_op(self, name: str, input: Any) -> OpInfo:
        overloads = [op for op in self.ops.values() if op.signature.matches_name(name)]
        if len(overloads) == 1:
            return overloads[0]
        if len(overloads) == 0:
            raise Exception(f"unknown operation `{name}`")

        matches = [op for op in overloads if op.signature.matches_input(input)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) == 0:
            example_op = overloads[0]
            assert (input_param := example_op.signature.input_param) is not None
            try:
                type_check_value(input, input_param.annotation)
            except DuqTypeError as e:
                raise DuqTypeError(
                    f"{example_op.name} (+{len(overloads) - 1} overloads): {e.args[0]}"
                )

        op_names = ", ".join(f"`{op.name}`" for op in matches)
        raise Exception(f"ambiguous operation `{name}`: {op_names}")

    def evaluate_op_expr(self, expr: OpExpr, input: Any) -> Any:
        args = []
        if expr.name.text.startswith("."):
            op = self.resolve_op("std.record.field", input)
            args.append(expr.name.text.removeprefix("."))
        elif expr.name.text == "{":
            op = self.resolve_op("map", input)
        else:
            op = self.resolve_op(expr.name.text, input)

        arg_exprs = () if expr.arg_list is None else expr.arg_list.args
        if op.signature.is_macro:
            args += arg_exprs
        else:
            args += [self.evaluate(arg_expr, input) for arg_expr in arg_exprs]

        args = tuple(args)
        call_args = op.signature.type_check_inputs(self, input, args)

        return op.op_func(*call_args)

    def evaluate_chain_expr(self, expr: ChainExpr, input: Any) -> Any:
        for subexpr in expr.exprs:
            input = self.evaluate(subexpr, input)
        return input

    def evaluate(self, expr: Expr, input: Any) -> Any:
        if expr.type == "literal":
            return expr.value
        elif expr.type == "op":
            return self.evaluate_op_expr(expr, input)
        elif expr.type == "chain":
            return self.evaluate_chain_expr(expr, input)
        else:
            assert_never(expr)


@dataclass
class Hinted[T]:
    hint: str
    value: T


def evaluate(source: str, input: Any = None) -> Any:
    context = DuqContext.create()
    expr = parse(source)
    return context.evaluate(expr, input)
