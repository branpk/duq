from dataclasses import dataclass
from typing import Any, Callable

from duq._type_check import OpSignature


@dataclass
class OpInfo:
    signature: OpSignature
    op_func: Callable


class Context:
    def __init__(self) -> None:
        self.ops: dict[str, OpInfo] = {}

    def load_op(self, name: str, op_func: Callable) -> None:
        if name in self.ops:
            raise Exception(f"redefined op: `{name}`")
        signature = OpSignature.of(name, op_func)
        self.ops[name] = OpInfo(signature, op_func)

    def load_ops(self, ops: dict[str, Callable]) -> None:
        for op_name, op_func in ops.items():
            self.load_op(op_name, op_func)

    def resolve_op(self, name: str, input: Any) -> OpInfo:
        op = self.ops.get(name)
        if op is None:
            raise Exception(f"unknown operation: `{name}`")
        return op


_global_context: Context | None = None


def global_context() -> Context:
    global _global_context
    if _global_context is None:
        import duq._std

        _global_context = Context()
        _global_context.load_ops(duq._std.op_definitions)
    return _global_context
