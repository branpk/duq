def op_float(input: str | int | float) -> float:
    return float(input)


def op_int(input: str | int) -> int:
    if isinstance(input, str):
        return int(input, base=0)
    else:
        return input


def op_add(input: int | float, arg: int | float) -> int | float:
    return input + arg


def op_sub(input: int | float, arg: int | float) -> int | float:
    return input - arg


def op_str(input: int | float) -> str:
    return str(input)


op_definitions = {
    "std.number.float": op_float,
    "std.number.int": op_int,
    "std.number.add": op_add,
    "std.number.sub": op_sub,
    "std.number.str": op_str,
}
