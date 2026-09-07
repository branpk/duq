from . import _number
from . import _str
from . import _list

op_definitions = {
    f"std.{op_name}": op_func
    for op_definitions in [
        _number.op_definitions,
        _str.op_definitions,
        _list.op_definitions,
    ]
    for op_name, op_func in op_definitions.items()
}
