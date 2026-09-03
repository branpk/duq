from typing import TypedDict

import bs4


class Proc(TypedDict):
    name: str
    args: list["Expr"]


type Expr = None | int | float | str | bool | Proc


type Value = None | int | float | str | bool | list[Value] | dict[str, Value] | bs4.Tag
