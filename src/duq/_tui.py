import json
from pathlib import Path
import sys

from prompt_toolkit import HTML, Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import fragment_list_to_text, to_formatted_text
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import (
    BufferControl,
    Dimension,
    HSplit,
    Layout,
    NumberedMargin,
    VSplit,
    Window,
)
from prompt_toolkit.layout.processors import (
    Processor,
    Transformation,
    TransformationInput,
)

from duq._preview import Preview


async def run_tui():
    state_file = Path("data/state.json")
    try:
        with open(state_file) as f:
            state = json.load(f)
    except:
        state = {"source": ""}

    key_bindings = KeyBindings()

    @key_bindings.add("c-c")
    @key_bindings.add("c-d")
    def _(event: KeyPressEvent) -> None:
        event.app.exit()

    def define_brace_handlers(brace_pair: str) -> None:
        lbrace = brace_pair[0]
        rbrace = brace_pair[1]

        @Condition
        def should_auto_close() -> bool:
            text = source_buffer.text
            pos = source_buffer.cursor_position
            if pos >= 1 and text[pos - 1] == "\\":
                return False
            if pos >= 1 and lbrace == rbrace and text[pos - 1] == lbrace:
                return False
            if pos < len(text) and (text[pos].isalnum() or text[pos] == "_"):
                return False
            return True

        @Condition
        def should_eat_closing_brace() -> bool:
            text = source_buffer.text
            pos = source_buffer.cursor_position
            if pos >= 1 and text[pos - 1] == "\\":
                return False
            if pos >= len(text):
                return False
            next = text[pos]
            return next == rbrace

        @Condition
        def is_in_empty_braces() -> bool:
            text = source_buffer.text
            pos = source_buffer.cursor_position
            if pos <= 0 or pos >= len(text):
                return False
            return text[pos - 1 : pos + 1] == brace_pair

        @key_bindings.add(lbrace, filter=should_auto_close)
        def _(event: KeyPressEvent) -> None:
            event.current_buffer.insert_text(brace_pair)
            event.current_buffer.cursor_left()

        @key_bindings.add(rbrace, filter=should_eat_closing_brace)
        def _(event: KeyPressEvent) -> None:
            event.current_buffer.cursor_right()

        @key_bindings.add("backspace", filter=is_in_empty_braces)
        def _(event: KeyPressEvent) -> None:
            event.current_buffer.cursor_right()
            event.current_buffer.delete_before_cursor(2)

    for brace_pair in ["()", "[]", "{}", '""', "''"]:
        define_brace_handlers(brace_pair)

    def on_source_changed(source_buffer: Buffer) -> None:
        preview.set_source(source_buffer.text)
        state["source"] = source_buffer.text
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    def on_cursor_position_changed(source_buffer: Buffer) -> None:
        preview.set_cursor_position(source_buffer.cursor_position)

    class FormattedHTMLProcessor(Processor):
        def apply_transformation(
            self, transformation_input: TransformationInput
        ) -> Transformation:
            text = fragment_list_to_text(transformation_input.fragments)
            return Transformation(to_formatted_text(HTML(text)))

    output_buffer = Buffer(read_only=True)
    error_buffer = Buffer(read_only=True)

    def set_output(text: str) -> None:
        pos = output_buffer.cursor_position
        output_buffer.set_document(Document(text), bypass_readonly=True)
        output_buffer.cursor_position = min(pos, len(output_buffer.text))

    def set_error(text: str) -> None:
        error_buffer.set_document(Document(text), bypass_readonly=True)

    preview = Preview(set_output=set_output, set_error=set_error)

    source_buffer = Buffer(
        on_text_changed=on_source_changed,
        on_cursor_position_changed=on_cursor_position_changed,
    )
    source_buffer.text = state["source"]
    source_buffer.cursor_position = len(source_buffer.text)

    split = HSplit(
        [
            Window(
                BufferControl(source_buffer),
                left_margins=[NumberedMargin()],
                dont_extend_height=True,
            ),
            Window(
                BufferControl(
                    output_buffer, input_processors=[FormattedHTMLProcessor()]
                ),
                left_margins=[NumberedMargin()],
                dont_extend_height=True,
                height=Dimension(1, 40),
            ),
            Window(
                BufferControl(error_buffer),
                left_margins=[],
                dont_extend_height=True,
            ),
        ],
        padding=1,
        padding_char="\u2500",
    )
    layout = Layout(split)

    app = Application(
        full_screen=False,
        mouse_support=True,
        key_bindings=key_bindings,
        layout=layout,
    )

    await app.run_async(set_exception_handler=False)
