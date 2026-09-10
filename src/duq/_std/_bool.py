def op_not(input: bool) -> bool:
    return not input


def op_str(input: bool) -> str:
    return str(input).lower()


op_definitions = {
    "std.bool.not": op_not,
    "std.bool.str": op_str,
}
