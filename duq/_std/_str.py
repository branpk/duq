def op_str(input: str) -> str:
    return input


def op_trim(input: str) -> str:
    return input.strip()


def op_rmPrefix(input: str, prefix: str) -> str:
    return input.removeprefix(prefix)


def op_rmSuffix(input: str, suffix: str) -> str:
    return input.removesuffix(suffix)


def op_join(input: list[str], separator: str = "") -> str:
    return separator.join(input)


op_definitions = {
    "str.str": op_str,
    "str.trim": op_trim,
    "str.rmPrefix": op_rmPrefix,
    "str.rmSuffix": op_rmSuffix,
    "str.join": op_join,
}
