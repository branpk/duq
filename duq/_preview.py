import asyncio
import html
import json
import re
from typing import Any, AsyncIterator, Awaitable, Callable, Iterable

import bs4

from duq._evaluation_v2 import Hinted, evaluate_chain
from duq._syntax import Expr, ExprList, OpExpr, parse
from duq._util import DuqFuture, DuqStream, Reactive


def truncate_expr(expr: Expr, cursor_position: int) -> tuple[Expr, bool]:
    if expr.type == "literal" or expr.arg_list is None:
        return expr, False
    arg_list, cursor_hint = expr.arg_list, False
    if cursor_position >= arg_list.span[0] and cursor_position <= arg_list.span[1]:
        # TODO: Better mechanism for this
        is_chain = expr.name.text in [
            "do",
            "map",
            "mapValues",
            "future.map",
            "stream.map",
            "{",
        ]
        arg_list, cursor_hint = (
            truncate_expr_list(arg_list, is_chain, cursor_position),
            is_chain,
        )
    return (
        OpExpr(type=expr.type, span=expr.span, name=expr.name, arg_list=arg_list),
        cursor_hint,
    )


def truncate_expr_list(
    expr_list: ExprList, is_chain: bool, cursor_position: int
) -> ExprList:
    exprs: list[Expr] = []
    nested_cursor_hint = False
    for expr in expr_list.exprs:
        if expr.span[0] >= cursor_position:
            break
        expr, cursor_hint = truncate_expr(expr, cursor_position)
        exprs.append(expr)
        nested_cursor_hint |= cursor_hint
    if is_chain and not nested_cursor_hint:
        exprs.append(parse("std.basic.hint('cursor')").exprs[0])
    return ExprList(span=expr_list.span, exprs=tuple(exprs))


def render_items(
    start: str, end: str, items: Iterable[str], indent: int, sep=","
) -> str:
    start = html.escape(start)
    end = html.escape(end)
    sep = html.escape(sep)
    indent_str = " " * indent
    if not items:
        return start + end
    elif len(result := start + (sep + " ").join(items) + end) < 40:
        return result
    else:
        result = start
        for item in items:
            result += html.escape("\n") + indent_str + "  " + item + sep
        result += html.escape("\n") + indent_str + end
        return result


def render_value(value: Any, indent=0) -> Reactive[str]:
    if value is None or isinstance(value, (int, float, str, bool)):
        return Reactive.of(html.escape(json.dumps(value)))
    elif isinstance(value, list):
        child_strs_rx = Reactive.from_list(
            [render_value(child, indent + 2) for child in value]
        )
        return child_strs_rx.map(
            lambda child_strs: render_items("[", "]", child_strs, indent)
        )
    elif isinstance(value, dict):
        child_strs_rx = Reactive.from_list(
            [
                render_value(child, indent + 2).map(
                    lambda s: f"{html.escape(json.dumps(key))}: {s}"
                )
                for key, child in value.items()
            ]
        )
        return child_strs_rx.map(
            lambda child_strs: render_items("{", "}", child_strs, indent)
        )
    elif isinstance(value, Awaitable):
        return Reactive.from_awaitable(value).flat_map(
            lambda child_maybe: (
                render_value(child_maybe.value, indent + 2)
                if child_maybe.is_some
                else Reactive.of("...")
            ).map(
                lambda child_str: render_items(
                    "future(", ")", [child_str], indent, sep=""
                )
            )
        )
    elif isinstance(value, DuqFuture):
        return render_value(value.create(), indent)
    elif isinstance(value, AsyncIterator):

        async def child_strs_iter() -> AsyncIterator[Reactive[str]]:
            async for child in value:
                yield render_value(child, indent + 2)

        return Reactive.collect_from_iter(child_strs_iter()).map(
            lambda child_strs: render_items(
                "stream[",
                "]",
                child_strs.items + ([] if child_strs.is_done else ["..."]),
                indent,
            )
        )
    elif isinstance(value, DuqStream):
        return render_value(value.create(), indent)
    elif isinstance(value, Hinted):
        child_rx = render_value(value.value, indent)
        if value.hint == "cursor":

            def bold(s: str) -> str:
                lines = s.split("\n")
                lines = [f"<green>{line}</green>" for line in lines]
                return "\n".join(lines)

            return child_rx.map(bold)
        else:
            return child_rx
    elif isinstance(value, bs4.Tag):
        indented = re.sub(
            r"^(\s*)",
            (indent * " ") + r"\1\1",
            value.prettify(),
            flags=re.MULTILINE,
        ).removeprefix(indent * " ")
        output = re.sub(r"\s*$", "", indented)
        return Reactive.of(html.escape(output))
    else:
        raise Exception(f"unimplemented: {type(value)}")


class Preview:
    def __init__(
        self, set_output: Callable[[str], None], set_error: Callable[[str], None]
    ) -> None:
        self.source = ""
        self.cursor_position = 0
        self.current_task: asyncio.Task | None = None
        self.set_output = set_output
        self.set_error = set_error
        self.refresh()

    def set_source(self, source: str) -> None:
        self.source = source
        self.refresh()

    def set_cursor_position(self, cursor_position: int) -> None:
        self.cursor_position = cursor_position
        self.refresh()

    def refresh(self) -> None:
        try:
            expr_list = parse(self.source)
            truncated = truncate_expr_list(expr_list, True, self.cursor_position)
            result = evaluate_chain(truncated.exprs, None)
        except Exception as e:
            self.set_error(f"Error: {e}")
        else:

            async def set_output_task():
                try:
                    output_rx = render_value(result)
                    self.set_output(output_rx.initial)
                    async for output in output_rx.updates:
                        self.set_output(output)
                except Exception as e:
                    while isinstance(e, ExceptionGroup):
                        e = e.exceptions[0]
                    self.set_error(f"Error: {e}")

            if self.current_task != None:
                self.current_task.cancel()
            self.current_task = asyncio.create_task(set_output_task())
            self.set_error("")


async def print_value_async(value: Any) -> None:
    value_str_rx = render_value(value)
    print(html.unescape(value_str_rx.initial))
    async for value_str in value_str_rx.updates:
        print(html.unescape(value_str))


def print_value(value: Any) -> None:
    value_str_rx = render_value(value)
    print(html.unescape(value_str_rx.initial))
