import asyncio
import sys

import duq

if len(sys.argv) != 2:
    print("Usage: duq '<source>'", file=sys.stderr)
    sys.exit(1)

source = sys.argv[1]
result = duq.evaluate(source)
asyncio.run(duq.print_value_async(result))
