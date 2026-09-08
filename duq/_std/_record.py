from typing import Any

from duq._evaluation import evaluate_chain
from duq._syntax import Expr


def op_map(input: dict[str, Any], *args: Expr) -> dict[str, Any]:
    return {key: evaluate_chain(args, value) for key, value in input.items()}


def op_field(input: dict[str, Any], field: str) -> Any:
    if field not in input:
        raise Exception(f"no such field: `{field}`")
    return input[field]


op_definitions = {
    "std.record.map": op_map,
    "std.record.field": op_field,
}
