from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal, TypedDict

type TokenKind = Literal[
    "eof",
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
    "{",
    "}",
]


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    span: tuple[int, int]
    text: str


@dataclass(frozen=True)
class LiteralExpr:
    type: Literal["literal"]
    span: tuple[int, int]
    literal: Token
    value: None | int | float | str | bool


@dataclass(frozen=True)
class OpExpr:
    type: Literal["op"]
    span: tuple[int, int]
    name: Token
    arg_list: ExprList | None


type Expr = LiteralExpr | OpExpr


@dataclass(frozen=True)
class ExprList:
    span: tuple[int, int]
    exprs: tuple[Expr, ...]


def lex(s: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    while s:
        kind: TokenKind
        if match := re.match(r"\s+", s):
            kind = "whitespace"
        elif match := re.match(r"#.*", s):
            kind = "comment"
        elif match := re.match(r"null\b", s):
            kind = "null"
        elif match := re.match(r"true\b|false\b", s):
            kind = "bool"
        elif match := re.match(r"\.?[\w_][\w\d_]*(\.[\w_][\w\d_]*)*", s):
            kind = "symbol"
        elif match := re.match(r"[-+]?[\d\.](e[-+]?|[\.\w\d_])*", s):
            if "." in match.group() or "e" in match.group():
                kind = "float"
            else:
                kind = "int"
        elif match := re.match(r"\"(\\\"|[^\"])*\"|\'(\\\'|[^\'])*\'", s):
            kind = "str"
        elif match := re.match(r"\(", s):
            kind = "("
        elif match := re.match(r"\)", s):
            kind = ")"
        elif match := re.match(r"\{", s):
            kind = "{"
        elif match := re.match(r"\}", s):
            kind = "}"
        else:
            raise Exception(f"failed to tokenize: {repr(s)}")

        span = (i, i + match.end())
        text = s[: match.end()]
        tokens.append(Token(kind=kind, span=span, text=text))
        s = s[match.end() :]
        i += match.end()
    tokens.append(Token(kind="eof", span=(i, i), text="<eof>"))
    return tokens


def parse_literal_expr(tokens: list[Token]) -> LiteralExpr:
    token = tokens.pop(0)
    if token.kind == "null":
        value = None
    elif token.kind == "bool":
        value = token.text == "true"
    elif token.kind == "int":
        value = int(token.text, base=0)
    elif token.kind == "float":
        value = float(token.text)
    elif token.kind == "str":
        value = eval(token.text)
    else:
        raise Exception(f"expected expression, found `{token.text}`")
    return LiteralExpr(type="literal", span=token.span, literal=token, value=value)


def parse_op_expr(tokens: list[Token]) -> OpExpr:
    head = tokens.pop(0)

    if head.kind == "{":
        arg_list = parse_expr_list(tokens)
        rbrace = tokens.pop(0)
        if rbrace.kind != "}":
            raise Exception(f"expected `}}`, found `{head.text}`")
        return OpExpr(
            type="op", span=(head.span[0], rbrace.span[1]), name=head, arg_list=arg_list
        )

    if head.kind != "symbol":
        raise Exception(f"expected operation, found `{head.text}`")
    while tokens[0].kind == "whitespace" or tokens[0].kind == "comment":
        tokens.pop(0)
    if tokens[0].kind == "(":
        tokens.pop(0)
        arg_list = parse_expr_list(tokens)
        rparen = tokens.pop(0)
        if rparen.kind != ")":
            raise Exception(f"expected `)`, found `{head.text}`")
        return OpExpr(
            type="op", span=(head.span[0], rparen.span[1]), name=head, arg_list=arg_list
        )
    else:
        return OpExpr(type="op", span=head.span, name=head, arg_list=None)


def parse_expr(tokens: list[Token]) -> Expr:
    if (
        tokens[0].kind == "symbol"
        or tokens[0].kind == "dotSymbol"
        or tokens[0].kind == "{"
    ):
        return parse_op_expr(tokens)
    else:
        return parse_literal_expr(tokens)


def parse_expr_list(tokens: list[Token]) -> ExprList:
    start = tokens[0].span[0]
    exprs: list[Expr] = []
    while tokens[0].kind != ")" and tokens[0].kind != "}" and tokens[0].kind != "eof":
        if tokens[0].kind == "whitespace" or tokens[0].kind == "comment":
            tokens.pop(0)
        else:
            exprs.append(parse_expr(tokens))
    end = tokens[0].span[0]
    return ExprList(span=(start, end), exprs=tuple(exprs))


def parse(source: str) -> ExprList:
    tokens = lex(source)
    expr_list = parse_expr_list(tokens)
    if tokens[0].kind != "eof":
        raise Exception(f"expected `<eof>`, found `{tokens[0].text}`")
    return expr_list
