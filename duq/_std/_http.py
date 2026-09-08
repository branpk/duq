import httpx

from duq._util import DuqFuture


def op_fetch(input: str) -> DuqFuture[str]:
    async def task() -> str:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                input,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
                },
            )
            if response.status_code != 200:
                raise Exception(f"request error: {input} -> {response.status_code}")
        return response.text

    return DuqFuture(task)


op_definitions = {
    "std.http.fetch": op_fetch,
}
