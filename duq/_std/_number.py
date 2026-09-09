def op_float(input: str | int | float) -> float:
    return float(input)


def op_int(input: str | int | float) -> int:
    if isinstance(input, str):
        return int(input, base=0)
    else:
        return int(input)


def op_add(input: int | float, arg: int | float) -> int | float:
    return input + arg


def op_sub(input: int | float, arg: int | float) -> int | float:
    return input - arg


def op_mul(input: int | float, arg: int | float) -> int | float:
    return input * arg


def op_div(input: int | float, arg: int | float) -> float:
    if arg == 0:
        return 0
    return input / arg


def op_gt(input: int | float, arg: int | float) -> bool:
    return input > arg


def op_even(input: int) -> bool:
    return input % 2 == 0


def op_odd(input: int) -> bool:
    return input % 2 == 1


def op_str(input: int | float) -> str:
    return str(input)


op_definitions = {
    "std.number.float": op_float,
    "std.number.int": op_int,
    "std.number.add": op_add,
    "std.number.sub": op_sub,
    "std.number.mul": op_mul,
    "std.number.div": op_div,
    "std.number.gt": op_gt,
    "std.number.even": op_even,
    "std.number.odd": op_odd,
    "std.number.str": op_str,
}
