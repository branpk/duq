import bs4


def op_html(input: str) -> bs4.BeautifulSoup:
    return bs4.BeautifulSoup(input, "html.parser")


def op_select(input: bs4.Tag, query: str) -> list[bs4.Tag]:
    return list(input.select(query))


def op_text(input: bs4.Tag) -> str:
    return input.text


op_definitions = {
    "std.html.html": op_html,
    "std.html.select": op_select,
    "std.html.text": op_text,
}
