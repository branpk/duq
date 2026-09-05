import asyncio
from dataclasses import dataclass
import dataclasses
import json
from typing import AsyncIterator, Awaitable, Callable, Iterable

import bs4

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


# type Value = (
#     | list[Value]
#     | dict[str, Value]
#     | Awaitable[Value]
#     | AsyncIterator[Value]
#     | bs4.Tag
# )


def render_items(
    start: str, end: str, items: Iterable[str], indent: int, sep=","
) -> str:
    indent_str = " " * indent
    if not items:
        return start + end
    elif len(result := start + (sep + " ").join(items) + end) < 40:
        return result
    else:
        result = start
        for item in items:
            result += "\n" + indent_str + "  " + item + sep
        result += "\n" + indent_str + end
        return result


def render_value_sync(value: Value, indent=0) -> str:
    if value is None or isinstance(value, (int, float, str, bool)):
        return json.dumps(value)
    elif isinstance(value, list):
        return render_items(
            "[",
            "]",
            [render_value_sync(item, indent + 2) for item in value],
            indent,
        )
    elif isinstance(value, dict):
        return render_items(
            "{",
            "}",
            [
                json.dumps(key) + ": " + render_value_sync(value, indent + 2)
                for key, value in value.items()
            ],
            indent,
        )
    elif isinstance(value, Awaitable):
        return "<future>"
    elif isinstance(value, AsyncIterator):
        return "<stream>"
    elif isinstance(value, bs4.Tag):
        return "<html>"


async def render_value(value: Value, indent=0) -> AsyncIterator[str]:
    if value is None or isinstance(value, (int, float, str, bool)):
        yield json.dumps(value)
    elif isinstance(value, list):
        items = ["..."] * len(value)
        yield render_items("[", "]", items, indent)

        queue = asyncio.Queue[None]()

        async def item_coroutine(i: int):
            async for output in render_value(value[i], indent + 2):
                items[i] = output
                await queue.put(None)

        async with asyncio.TaskGroup() as task_group:
            for i in range(len(value)):
                task_group.create_task(item_coroutine(i))

            while True:
                await queue.get()
                yield render_items("[", "]", items, indent)
    elif isinstance(value, Awaitable):
        yield render_items("future(", ")", ["..."], indent, sep="")
        try:
            result = await value
        except Exception as e:
            yield render_items("future(", ")", [f"Error: {e}"], indent, sep="")
        else:
            async for output in render_value(result, indent + 2):
                yield render_items("future(", ")", [output], indent, sep="")
    elif isinstance(value, AsyncIterator):
        items: list[str] = []
        yield render_items("stream[", "]", ["..."], indent)
        async for item in value:
            items.append(render_value_sync(item, indent + 2))
            yield render_items("stream[", "]", items + ["..."], indent)
        yield render_items("stream[", "]", items, indent)
    else:
        yield render_value_sync(value, indent)


class Preview:
    def __init__(
        self, set_output: Callable[[str], None], set_error: Callable[[str], None]
    ) -> None:
        self.source = ""
        self.cursor_position = 0
        self.current_task: asyncio.Task | None = None
        self.set_output = set_output
        self.set_error = set_error

        set_output("null")
        set_error("")

    def set_source(self, source: str) -> None:
        self.source = source
        self.refresh()

    def set_cursor_position(self, cursor_position: int) -> None:
        self.cursor_position = cursor_position
        self.refresh()

    def refresh(self) -> None:
        try:
            expr_list = parse(self.source)
            truncated = truncate_expr_list(expr_list, self.cursor_position)
            result = evaluate_chain(truncated.exprs, None)
        except Exception as e:
            self.set_error(f"Error: {e}")
        else:

            async def set_output_task():
                async for output in render_value(result):
                    self.set_output(output)

            if self.current_task != None:
                self.current_task.cancel()
            self.current_task = asyncio.create_task(set_output_task())
            self.set_error("")
