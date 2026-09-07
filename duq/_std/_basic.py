from typing import Any

from duq._evaluation_v2 import Hinted, evaluate_chain
from duq._syntax import Expr


def op_id(input: Any, *args: Expr) -> Any:
    return evaluate_chain(args, input)


def op_eq(input: Any, arg: Any) -> bool:
    return input == arg


def op_hint(input: Any, hint: str) -> Hinted[Any]:
    return Hinted(hint, input)


op_definitions = {
    "std.basic.id": op_id,
    "std.basic.eq": op_eq,
    "std.basic.hint": op_hint,
}
