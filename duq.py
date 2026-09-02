import json
import re
from typing import Any, TypedDict
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
    raw_args = expr["args"]

    ## Macros

    # basic
    if proc_name == "do":
        return evaluate_chain(raw_args, inp)

    # list
    elif proc_name == "map":
        assert type(inp) == list
        result = []
        for item in inp:
            result.append(evaluate_chain(raw_args, item))
        return result
    elif proc_name == "filter":
        assert type(inp) == list
        result = []
        for item in inp:
            cond = evaluate_chain(raw_args, item)
            assert type(cond) == bol
            if cond:
                result.append(item)
        return result
    elif proc_name == "groupBy":
        assert type(inp) == list
        result = {}
        for item in inp:
            key = evaluate_chain(raw_args, item)
            assert type(key) == str
            result.setdefault(key, []).append(item)
        return result
    elif proc_name == "keyBy":
        assert type(inp) == list
        result = {}
        for item in inp:
            key = evaluate_chain(raw_args, item)
            assert type(key) == str
            assert key not in result
            result[key] = item
        return result

    # record
    elif proc_name == "mapValues":
        assert type(inp) == dict
        return {key: evaluate_chain(raw_args, value) for key, value in inp.items()}

    ## Functions

    args = [evaluate_expr(arg, inp) for arg in raw_args]

    # basic
    if proc_name == "id":
        assert len(args) == 0
        return inp
    elif proc_name == "eq":
        assert len(args) == 1
        assert type(args[0]) == type(inp)
        assert type(inp) in [int, str]
        return inp == args[0]

    # number
    elif proc_name == "float":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) in [str, int, float]
        return float(arg)
    elif proc_name == "int":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) in [str, int]
        return int(arg, base=0)
    elif proc_name == "add":
        assert len(args) == 1
        assert type(args[0]) in [int, float]
        assert type(inp) in [int, float]
        return inp + args[0]
    elif proc_name == "sub":
        assert len(args) == 1
        assert type(args[0]) in [int, float]
        assert type(inp) in [int, float]
        return inp - args[0]

    # str
    elif proc_name == "str":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) in [str, int, float, bool]
        if type(arg) == bool:
            return str(arg).lower()
        return str(arg)
    elif proc_name == "trim":
        assert len(args) == 0
        assert type(inp) == str
        return inp.strip()
    elif proc_name == "rmPrefix":
        assert len(args) == 1
        assert type(args[0]) == str
        assert type(inp) == str
        return inp.removeprefix(args[0])
    elif proc_name == "rmSuffix":
        assert len(args) == 1
        assert type(args[0]) == str
        assert type(inp) == str
        return inp.removesuffix(args[0])
    elif proc_name == "join":
        assert len(args) == 0 or len(args) == 1
        sep = "" if len(args) == 0 else args[0]
        assert type(sep) == str
        assert type(inp) == list
        for item in inp:
            assert type(item) == str
        return sep.join(inp)

    # list
    elif proc_name == "list":
        return args
    elif proc_name == "index":
        assert len(args) == 1
        index = args[0]
        assert type(index) == int
        assert type(inp) == list
        assert index >= -len(inp) and index < len(inp)
        return inp[index]
    elif proc_name == "slice":
        assert len(args) == 1 or len(args) == 2
        assert type(inp) == list
        if len(args) == 1:
            start = args[0]
            end = len(inp)
        else:
            start = args[0]
            end = args[1]
        assert type(start) == int
        assert type(end) == int
        start = max(start, 0)
        end = min(end, len(inp))
        if start >= end:
            return []
        else:
            return inp[start:end]
    elif proc_name == "flatten":
        assert len(args) == 0
        assert type(inp) == list
        result = []
        for item in inp:
            assert type(item) == list
            result += item
        return result
    elif proc_name == "range":
        assert len(args) == 1 or len(args) == 2
        if len(args) == 1:
            start = 0
            end = args[0]
        else:
            start = args[0]
            end = args[1]
        assert type(start) == int
        assert type(end) == int
        return list(range(start, end))
    elif proc_name == "count":
        assert len(args) == 0
        assert type(inp) == list
        return len(inp)
    elif proc_name == "sum":
        assert len(args) == 0
        assert type(inp) == list
        total = 0
        for item in inp:
            assert type(item) in [int, float]
            total += item
        return total
    elif proc_name == "mean":
        assert len(args) == 0
        assert type(inp) == list
        if len(inp) == 0:
            return 0.0
        total = 0
        for item in inp:
            assert type(item) in [int, float]
            total += item
        return total / len(inp)

    # record
    elif proc_name == "field":
        assert len(args) == 1
        assert type(args[0]) == str
        assert type(inp) == dict
        assert args[0] in inp
        return inp[args[0]]

    # file
    elif proc_name == "file.read":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) == str
        with open(arg, "r") as f:
            return f.read()

    # http
    elif proc_name == "http.fetch":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) == str
        response = requests.get(
            arg,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
            },
        )
        if not response.ok:
            raise Exception(f"request error: {arg} -> {response.status_code}")
        return response.text

    # json
    elif proc_name == "json":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        assert type(arg) == str
        return json.loads(arg)
    elif proc_name == "json.pretty":
        assert len(args) == 0 or len(args) == 1
        arg = inp if len(args) == 0 else args[0]
        return json.dumps(arg, indent=2)

    # html
    elif proc_name == "html":
        assert len(args) == 0
        assert type(inp) == str
        return bs4.BeautifulSoup(inp, "html.parser")
    elif proc_name == "html.select":
        assert len(args) == 1
        assert type(args[0]) == str
        assert isinstance(inp, bs4.Tag)
        return list(inp.select(args[0]))
    elif proc_name == "html.text":
        assert len(args) == 0
        assert isinstance(inp, bs4.Tag)
        return inp.text

    raise Exception(f"unknown procedure: {proc_name}")


def evaluate_chain(exprs: list[Expr], inp: Value) -> Value:
    for expr in exprs:
        inp = evaluate_expr(expr, inp)
    return inp


def evaluate(source: str, inp: Value = None) -> Value:
    exprs = parse(source)
    return evaluate_chain(exprs, inp)
