import json
from pathlib import Path

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import (
    BufferControl,
    HSplit,
    Layout,
    NumberedMargin,
    VSplit,
    Window,
)

import duq


def run_tui():
    state_file = Path("data/state.json")
    try:
        with open(state_file) as f:
            state = json.load(f)
    except:
        state = {"source": ""}

    key_bindings = KeyBindings()

    @key_bindings.add("c-c")
    def exit_(event: KeyPressEvent) -> None:
        event.app.exit()

    def on_source_changed(source_buffer: Buffer) -> None:
        source = source_buffer.text
        try:
            output = json.dumps(duq.evaluate(source), indent=2)
        except Exception as e:
            output = f"Error: {e}"
        output_buffer.text = output

        state["source"] = source
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    source_buffer = Buffer(on_text_changed=on_source_changed)
    output_buffer = Buffer()

    source_buffer.text = state["source"]
    source_buffer.cursor_position = len(source_buffer.text)

    split = HSplit(
        [
            Window(
                BufferControl(source_buffer),
                left_margins=[NumberedMargin()],
                dont_extend_height=True,
            ),
            Window(BufferControl(output_buffer), left_margins=[NumberedMargin()]),
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

    app.run()
