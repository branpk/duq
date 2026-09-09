import asyncio
import html
import json
import re
from typing import Any, AsyncIterator, Awaitable, Callable, Iterable

import bs4

from duq._evaluation import DuqContext, Hinted
from duq._syntax import parse
from duq._util import DuqFuture, DuqStream, Reactive


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
        self.ctx = DuqContext.create()
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
            expr = parse(self.source, self.cursor_position)
            self.ctx.cursor = self.cursor_position
            result = self.ctx.evaluate(expr, None)
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
