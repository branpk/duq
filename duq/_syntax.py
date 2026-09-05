import re
from typing import Literal, TypedDict

type TokenKind = Literal[
    "whitespace",
    "comment",
    "null",
    "bool",
    "float",
    "int",
    "str",
    "symbol",
    "(",
    ")",
]


class Token(TypedDict):
    kind: TokenKind
    span: tuple[int, int]
    text: str


class OpExpr(TypedDict):
    name: str
    args: list["Expr"]


type Expr = None | int | float | str | bool | OpExpr


def lex(s: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    while s:
        kind: TokenKind
        if match := re.match(r"\s+", s):
            kind = "whitespace"
        elif match := re.match(r"#.*", s):
            kind = "comment"
        elif match := re.match("null\b", s):
            kind = "null"
        elif match := re.match(r"true\b|false\b", s):
            kind = "bool"
        elif match := re.match(r"[-+]?[\d\.](e[-+]?|[\.\w\d_])*", s):
            if "." in match.group() or "e" in match.group():
                kind = "float"
            else:
                kind = "int"
        elif match := re.match(r"\"(\\\"|[^\"])*\"|\'(\\\'|[^\'])*\'", s):
            kind = "str"
        elif match := re.match(r"[\w_][\w\d_]*(\.[\w_][\w\d_]*)*", s):
            kind = "symbol"
        elif match := re.match(r"\(", s):
            kind = "("
        elif match := re.match(r"\)", s):
            kind = ")"
        else:
            raise Exception(f"failed to tokenize: {repr(s)}")

        span = (i, i + match.end())
        text = s[: match.end()]
        tokens.append(Token(kind=kind, span=span, text=text))
        s = s[match.end() :]
    return tokens


def get_token_value(
    token: Token,
) -> None | int | float | str | bool | Literal["trivia", "symbol", "(", ")"]:
    token_kind = token["kind"]
    token_text = token["text"]
    if token_kind == "whitespace" or token_kind == "comment":
        return "trivia"
    elif token_kind == "null":
        return None
    elif token_kind == "bool":
        return token_text == "true"
    elif token_kind == "int":
        return int(token_text, base=0)
    elif token_kind == "float":
        return float(token_text)
    elif token_kind == "str":
        return eval(token_text)
    else:
        return token_kind


def parse(s: str) -> list[Expr]:
    stack: list[list[Expr]] = [[]]
    can_accept_args = False
    for token in lex(s):
        token_value = get_token_value(token)
        if token_value == "trivia":
            pass
        elif token_value == "symbol":
            stack[-1].append({"name": token["text"], "args": []})
            can_accept_args = True
        elif token_value == "(":
            if not can_accept_args:
                raise Exception("invalid arg list")
            stack.append([])
            can_accept_args = False
        elif token_value == ")":
            if len(stack) <= 1:
                raise Exception("unbalanced parentheses")
            args = stack.pop()
            assert type(stack[-1][-1]) == dict
            stack[-1][-1]["args"] = args
            can_accept_args = False
        else:
            stack[-1].append(token_value)
            can_accept_args = False
    if len(stack) != 1:
        raise Exception("unbalanced parentheses")
    return stack[0]
