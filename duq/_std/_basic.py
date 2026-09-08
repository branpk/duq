from datetime import datetime
from typing import Any

from duq._evaluation import Context, Hinted
from duq._syntax import Expr


def op_id(ctx: Context, input: Any, *args: Expr) -> Any:
    return ctx.evaluate_chain(args, input)


def op_eq(input: Any, arg: Any) -> bool:
    return input == arg


def op_hint(input: Any, hint: str) -> Hinted[Any]:
    return Hinted(hint, input)


def op_now() -> str:
    return datetime.now().isoformat(timespec="milliseconds") + "Z"


def op_try(ctx: Context, input: Any, *args: Expr) -> Any:
    try:
        return ctx.evaluate_chain(args, input)
    except:
        return None


op_definitions = {
    "std.basic.id": op_id,
    "std.basic.eq": op_eq,
    "std.basic.hint": op_hint,
    "std.time.now": op_now,
    "std.basic.try": op_try,
}
