from duq._std import _basic
from duq._std import _bool
from duq._std import _list
from duq._std import _null
from duq._std import _number
from duq._std import _str

op_definitions = {
    op_name: op_func
    for op_definitions in [
        _basic.op_definitions,
        _bool.op_definitions,
        _list.op_definitions,
        _null.op_definitions,
        _number.op_definitions,
        _str.op_definitions,
    ]
    for op_name, op_func in op_definitions.items()
}
