from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from duq._syntax import Expr, parse
from duq._type_check import DuqTypeError, OpSignature, type_check_value


@dataclass
class OpInfo:
    name: str
    signature: OpSignature
    op_func: Callable


class Context:
    def __init__(self) -> None:
        self.ops: dict[str, OpInfo] = {}
        self.cache: dict[str, Any] = {}

    @staticmethod
    def create() -> Context:
        import duq._std

        context = Context()
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

    def evaluate_expr(self, expr: Expr, input: Any) -> Any:
        if expr.type == "literal":
            return expr.value

        while isinstance(input, Hinted):
            input = input.value

        args = []
        if expr.name.text.startswith("."):
            op = self.resolve_op("std.record.field", input)
            args.append(expr.name.text.removeprefix("."))
        elif expr.name.text == "{":
            op = self.resolve_op("map", input)
        else:
            op = self.resolve_op(expr.name.text, input)

        arg_exprs = () if expr.arg_list is None else expr.arg_list.exprs
        if op.signature.is_macro:
            args += arg_exprs
        else:
            for arg_expr in arg_exprs:
                arg = self.evaluate_expr(arg_expr, input)
                while isinstance(arg, Hinted):
                    arg = arg.value
                args.append(arg)

        args = tuple(args)
        op.signature.type_check_inputs(input, args)

        call_args = op.signature.get_call_args(self, input, args)
        return op.op_func(*call_args)

    def evaluate_chain(self, exprs: Iterable[Expr], input: Any) -> Any:
        for expr in exprs:
            input = self.evaluate_expr(expr, input)
        return input


@dataclass
class Hinted[T]:
    hint: str
    value: T


def evaluate(source: str, input: Any = None) -> Any:
    context = Context.create()
    expr_list = parse(source)
    return context.evaluate_chain(expr_list.exprs, input)
