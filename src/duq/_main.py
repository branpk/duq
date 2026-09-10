import asyncio
import sys
import warnings

import duq


def cli():
    def catch_warning(message, category, filename, lineno, file=None, line=None):
        pass

    warnings.showwarning = catch_warning
    # warnings.filterwarnings(
    #     "ignore", message=".*was never awaited.*", category=RuntimeWarning
    # )
    # warnings.filterwarnings(
    #     "ignore", message=".*invalid escape sequence.*", category=SyntaxWarning
    # )

    if len(sys.argv) == 1:
        asyncio.run(duq.run_tui())
        sys.exit(0)

    if len(sys.argv) != 2:
        print("Usage: duq '<source>'", file=sys.stderr)
        sys.exit(1)

    source = sys.argv[1]
    result = duq.evaluate(source)
    asyncio.run(duq.print_value_async(result))
