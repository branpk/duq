import re

from duq._types import Expr


def parse(s: str) -> list[Expr]:
    stack: list[list[Expr]] = [[]]
    can_accept_args = False
    while s:
        if match := re.match(r"\s+", s):
            pass
        elif match := re.match(r"#.*", s):
            pass
        elif match := re.match("null\b", s):
            stack[-1].append(None)
            can_accept_args = False
        elif match := re.match(r"true\b|false\b", s):
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
