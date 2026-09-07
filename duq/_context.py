from dataclasses import dataclass
from typing import Any, Callable

from duq._type_check import DuqTypeError, OpSignature, type_check_value


@dataclass
class OpInfo:
    name: str
    signature: OpSignature
    op_func: Callable


class Context:
    def __init__(self) -> None:
        self.ops: dict[str, OpInfo] = {}

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


_global_context: Context | None = None


def global_context() -> Context:
    global _global_context
    if _global_context is None:
        import duq._std

        _global_context = Context()
        _global_context.load_ops(duq._std.op_definitions)
    return _global_context
