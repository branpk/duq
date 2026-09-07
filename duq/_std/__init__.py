from . import _bool
from . import _list
from . import _null
from . import _number
from . import _str

op_definitions = {
    op_name: op_func
    for op_definitions in [
        _bool.op_definitions,
        _list.op_definitions,
        _null.op_definitions,
        _number.op_definitions,
        _str.op_definitions,
    ]
    for op_name, op_func in op_definitions.items()
}
