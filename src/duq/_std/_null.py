from typing import Any


def op_str(input: None) -> str:
    return "null"


def op_ifNull(input: Any, value: Any) -> Any:
    if input is None:
        return value
    else:
        return input


op_definitions = {
    "std.null.str": op_str,
    "std.null.ifNull": op_ifNull,
}
