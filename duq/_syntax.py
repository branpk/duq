from __future__ import annotations

from dataclasses import dataclass
import os
import re
import sys
from typing import Literal

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
    ",",
]


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    span: tuple[int, int]
    text: str


@dataclass(frozen=True)
class LiteralExpr:
    type: Literal["literal"]
    span: tuple[int, int]  # tight
    literal: Token
    value: None | int | float | str | bool

    def dbg_format(self) -> str:
        return self.literal.text

    def dbg_print(self, source: str, indent=0) -> None:
        print(
            " " * indent + f"literal {self.value} |{source[self.span[0]:self.span[1]]}|"
        )


@dataclass(frozen=True)
class ArgList:
    span: tuple[int, int]  # just after the lparen to just before the rparen
    args: tuple[Expr, ...]

    def dbg_format(self) -> str:
        return ", ".join(arg.dbg_format() for arg in self.args)

    def dbg_print(self, source: str, indent=0) -> None:
        print(" " * indent + f"arglist |{source[self.span[0]:self.span[1]]}|")
        for expr in self.args:
            expr.dbg_print(source, indent + 2)


@dataclass(frozen=True)
class OpExpr:
    type: Literal["op"]
    span: tuple[int, int]  # tight
    name: Token
    arg_list: ArgList | None

    def dbg_format(self) -> str:
        if self.arg_list:
            return f"{self.name.text}({self.arg_list.dbg_format()})"
        else:
            return self.name.text

    def dbg_print(self, source: str, indent=0) -> None:
        print(
            " " * indent + f"op {self.name.text} |{source[self.span[0]:self.span[1]]}|"
        )
        if self.arg_list:
            self.arg_list.dbg_print(source, indent + 2)


@dataclass(frozen=True)
class ChainExpr:
    type: Literal["chain"]
    span: tuple[int, int]  # includes all trivia before and after the exprs
    exprs: tuple[Expr, ...]

    def dbg_format(self) -> str:
        return " ".join(expr.dbg_format() for expr in self.exprs)

    def dbg_print(self, source: str, indent=0) -> None:
        print(" " * indent + f"chain |{source[self.span[0]:self.span[1]]}|")
        for expr in self.exprs:
            expr.dbg_print(source, indent + 2)


type Expr = LiteralExpr | OpExpr | ChainExpr


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
        elif match := re.match(
            r"\.?[a-zA-Z_][a-zA-Z\d_]*(\.[a-zA-Z_][a-zA-Z\d_]*)*", s
        ):
            kind = "symbol"
        elif match := re.match(r"[-+]?[\d\.](e[-+]?|[\.a-fA-F\d_])*", s):
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
        elif match := re.match(r",", s):
            kind = ","
        else:
            raise Exception(f"failed to tokenize: {repr(s)}")

        span = (i, i + match.end())
        text = s[: match.end()]
        tokens.append(Token(kind=kind, span=span, text=text))
        s = s[match.end() :]
        i += match.end()
    tokens.append(Token(kind="eof", span=(i, i), text="<eof>"))
    return tokens


def skip_trivia(tokens: list[Token]) -> None:
    while tokens[0].kind == "whitespace" or tokens[0].kind == "comment":
        tokens.pop(0)


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


def parse_arg_list(tokens: list[Token], cursor: int | None) -> ArgList:
    start = tokens[0].span[0]
    args: list[Expr] = []
    while True:
        arg = parse_chain_expr(tokens, cursor)
        if len(arg.exprs) == 0:
            if tokens[0].kind == ")" or tokens[0].kind == "}":
                break
            else:
                raise Exception(f"expected expression, found `{tokens[0].text}`")
        args.append(arg)

        if tokens[0].kind == ",":
            tokens.pop(0)
        else:
            break
    end = tokens[0].span[0]
    return ArgList(span=(start, end), args=tuple(args))


def parse_op_expr(tokens: list[Token], cursor: int | None) -> OpExpr:
    head = tokens.pop(0)

    if head.kind == "{":
        arg_list = parse_arg_list(tokens, cursor)
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
        arg_list = parse_arg_list(tokens, cursor)
        rparen = tokens.pop(0)
        if rparen.kind != ")":
            raise Exception(f"expected `)`, found `{head.text}`")
        return OpExpr(
            type="op", span=(head.span[0], rparen.span[1]), name=head, arg_list=arg_list
        )
    else:
        return OpExpr(type="op", span=head.span, name=head, arg_list=None)


def parse_atom_expr(tokens: list[Token], cursor: int | None) -> Expr:
    if (
        tokens[0].kind == "symbol"
        or tokens[0].kind == "dotSymbol"
        or tokens[0].kind == "{"
    ):
        return parse_op_expr(tokens, cursor)
    else:
        return parse_literal_expr(tokens)


def make_cursor_hint(span: tuple[int, int]) -> Expr:
    return OpExpr(
        type="op",
        span=span,
        name=Token(kind="symbol", span=span, text="hint"),
        arg_list=ArgList(
            span=span,
            args=(
                LiteralExpr(
                    type="literal",
                    span=span,
                    literal=Token(kind="str", span=span, text='"cursor"'),
                    value="cursor",
                ),
            ),
        ),
    )


def parse_chain_expr(tokens: list[Token], cursor: int | None) -> ChainExpr:
    start = tokens[0].span[0]
    exprs: list[Expr] = []

    skip_trivia(tokens)
    while (
        tokens[0].kind != ")"
        and tokens[0].kind != "}"
        and tokens[0].kind != ","
        and tokens[0].kind != "eof"
    ):
        expr = parse_atom_expr(tokens, cursor)
        exprs.append(expr)
        skip_trivia(tokens)

    end = tokens[0].span[0]

    if cursor is not None and cursor >= start and cursor <= end:
        nested_cursor = False
        for expr in exprs:
            if (
                isinstance(expr, OpExpr)
                and expr.arg_list is not None
                and cursor >= expr.arg_list.span[0]
                and cursor <= expr.arg_list.span[1]
            ):
                nested_cursor = True
                break

        if not nested_cursor:
            for i, expr in enumerate(exprs):
                if cursor <= expr.span[0]:
                    break
            else:
                i = len(exprs)
            exprs.insert(i, make_cursor_hint((cursor - 1, cursor + 1)))

    return ChainExpr(type="chain", span=(start, end), exprs=tuple(exprs))


def parse(source: str, cursor: int | None = None) -> Expr:
    tokens = lex(source)
    expr_list = parse_chain_expr(tokens, cursor)
    if tokens[0].kind != "eof":
        raise Exception(f"expected `<eof>`, found `{tokens[0].text}`")
    return expr_list


if __name__ == "__main__":
    source = sys.argv[1]
    if "|" in source:
        cursor = source.index("|")
        source = source[:cursor] + source[cursor + 1 :]
    else:
        cursor = None
    expr = parse(source, cursor)
    print("-" * os.get_terminal_size()[0])
    print(source)
    print("-" * os.get_terminal_size()[0])
    print(expr.dbg_format())
    print("-" * os.get_terminal_size()[0])
    expr.dbg_print(source)
    print("-" * os.get_terminal_size()[0])
