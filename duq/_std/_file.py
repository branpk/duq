def op_read(input: str) -> str:
    with open(input, "r") as f:
        return f.read()


op_definitions = {
    "std.file.read": op_read,
}
