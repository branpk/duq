import json
import re
from typing import Any, Callable, TypedDict
import bs4
import requests


class Proc(TypedDict):
    name: str
    args: list["Expr"]


type Expr = int | float | str | bool | Proc


def parse(s: str) -> list[Expr]:
    stack: list[list[Expr]] = [[]]
    can_accept_args = False
    while s:
        if match := re.match(r"\s+", s):
            pass
        elif match := re.match(r"#.*", s):
            pass
        elif match := re.match(r"true|false", s):
            stack[-1].append(match.group() == "true")
            can_accept_args = False
        elif match := re.match(r"[-+]?[\d\.](e[-+]?|[\.\w\d_])*", s):
            if "." in match.group() or "e" in match.group():
                value = float(match.group())
            else:
                value = int(match.group(), base=0)
            stack[-1].append(value)
            can_accept_args = False
        elif match := re.match(r"\"(\\\"|[^\"])*\"|\'(\\\'|[^\'])*\'", s):
            stack[-1].append(eval(match.group()))
            can_accept_args = False
        elif match := re.match(r"[\w_][\w\d_]*(\.[\w_][\w\d_]*)*", s):
            stack[-1].append({"name": match.group(), "args": []})
            can_accept_args = True
        elif match := re.match(r"\(", s):
            if not can_accept_args:
                raise Exception("invalid arg list")
            stack.append([])
            can_accept_args = False
        elif match := re.match(r"\)", s):
            if len(stack) <= 1:
                raise Exception("unbalanced parentheses")
            args = stack.pop()
            assert type(stack[-1][-1]) == dict
            stack[-1][-1]["args"] = args
            can_accept_args = False
        else:
            raise Exception(f"failed to tokenize: {repr(s)}")
        s = s[match.end() :]
    if len(stack) != 1:
        raise Exception("unbalanced parentheses")
    return stack[0]


type Value = Any


def evaluate_expr(expr: Expr, inp: Value) -> Value:
    if type(expr) in [int, float, str, bool]:
        return expr
    assert type(expr) == dict

    proc_name = expr["name"]
    args = [evaluate_expr(arg, inp) for arg in expr["args"]]
    if proc_name == "id":
        assert len(args) == 0
        return inp
    elif proc_name == "json":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) == str
        return json.loads(arg)
    elif proc_name == "json.pretty":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        return json.dumps(arg, indent=2)


def evaluate_chain(exprs: list[Expr], inp: Value) -> Value:
    for expr in exprs:
        inp = evaluate_expr(expr, inp)
    return inp


def evaluate(source: str, inp: Value = None) -> Value:
    exprs = parse(source)
    return evaluate_chain(exprs, inp)
