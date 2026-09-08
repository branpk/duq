from typing import Any


def op_tableToRecords(input: list[list[str]]) -> list[dict[str, str]]:
    if len(input) == 0:
        raise Exception("missing header row")
    headers = input[0]
    rows = input[1:]
    result = []
    for row in rows:
        record = {}
        for i, header in enumerate(headers):
            record[header] = None if i >= len(row) else row[i]
        result.append(record)
    return result


op_definitions = {
    "std.csv.tableToRecords": op_tableToRecords,
}
