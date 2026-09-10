import json
from typing import Any


def op_json(input: str) -> Any:
    return json.loads(input)


def op_pretty(input: Any) -> str:
    return json.dumps(input, indent=2)


op_definitions = {
    "std.json.json": op_json,
    "std.json.pretty": op_pretty,
}
