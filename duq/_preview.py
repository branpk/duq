import json

from duq._evaluation import evaluate, Value
from duq._syntax import lex


class Preview:
    def __init__(self) -> None:
        self.source = ""
        self.cursor_position = 0

    def set_source(self, source: str) -> None:
        self.source = source

    def set_cursor_position(self, cursor_position: int) -> None:
        self.cursor_position = cursor_position

    def evaluate(self) -> Value:
        tokens = lex(self.source)
        for token in tokens:
            pass

    def get_output(self) -> str:
        try:
            return json.dumps(evaluate(self.source[: self.cursor_position]), indent=2)
        except Exception as e:
            return f"Error: {e}"
