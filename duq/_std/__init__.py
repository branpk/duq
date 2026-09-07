from duq._std import (
    _basic,
    _file,
    _future,
    _html,
    _json,
    _bool,
    _list,
    _null,
    _number,
    _record,
    _str,
    _stream,
)

op_definitions = {
    op_name: op_func
    for op_definitions in [
        _basic.op_definitions,
        _bool.op_definitions,
        _file.op_definitions,
        _future.op_definitions,
        _html.op_definitions,
        _json.op_definitions,
        _list.op_definitions,
        _null.op_definitions,
        _number.op_definitions,
        _record.op_definitions,
        _str.op_definitions,
        _stream.op_definitions,
    ]
    for op_name, op_func in op_definitions.items()
}
