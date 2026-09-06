from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Awaitable, Callable, Literal, TypedDict


@dataclass
class Maybe[T]:
    is_some: bool
    optional_value: T | None

    @staticmethod
    def some(value: T) -> Maybe[T]:
        return Maybe(is_some=True, optional_value=value)

    @staticmethod
    def none() -> Maybe[T]:
        return Maybe(is_some=False, optional_value=None)

    @property
    def value(self) -> T:
        assert self.is_some
        return self.optional_value  # type: ignore


@dataclass
class CollectedIter[T]:
    is_done: bool
    items: list[T]


@dataclass
class Reactive[T]:
    initial: T
    updates: AsyncIterator[T]

    @staticmethod
    def of[V](value: V) -> Reactive[V]:
        async def updates() -> AsyncIterator[V]:
            if False:
                yield value

        return Reactive(value, updates())

    @staticmethod
    def from_list[V](values: list[Reactive[V]]) -> Reactive[list[V]]:
        initial = [value.initial for value in values]
        queue = asyncio.Queue[tuple[int, V]]()

        async def item_coroutine(i: int) -> None:
            async for new_value in values[i].updates:
                await queue.put((i, new_value))

        async def updates() -> AsyncIterator[list[V]]:
            current = list(initial)
            async with asyncio.TaskGroup() as task_group:
                for i in range(len(values)):
                    task_group.create_task(item_coroutine(i))

                while True:
                    i, new_value = await queue.get()
                    current = list(current)
                    current[i] = new_value
                    yield current

        return Reactive(initial, updates())

    @staticmethod
    def collect_from_iter[V](
        iter: AsyncIterator[Reactive[V]],
    ) -> Reactive[CollectedIter[V]]:
        queue = asyncio.Queue[
            tuple[int, V] | Literal["list-done"] | Literal["all-done"]
        ]()

        async def put_all_values(i: int, values: AsyncIterator[V]) -> None:
            async for value in values:
                await queue.put((i, value))

        async def add_all_items() -> None:
            async with asyncio.TaskGroup() as task_group:
                i = 0
                async for value in iter:
                    await queue.put((i, value.initial))
                    task_group.create_task(put_all_values(i, value.updates))
                    i += 1
                await queue.put("list-done")
            await queue.put("all-done")

        async def updates() -> AsyncIterator[CollectedIter[V]]:
            async with asyncio.TaskGroup() as task_group:
                task_group.create_task(add_all_items())

                current: list[V] = []
                list_done = False
                while True:
                    message = await queue.get()
                    if message == "all-done":
                        break
                    if message == "list-done":
                        list_done = True
                        yield CollectedIter(list_done, list(current))
                        continue

                    i, value = message
                    current = list(current)
                    if i >= len(current):
                        assert i == len(current)
                        current.append(value)
                    else:
                        current[i] = value
                    yield CollectedIter(list_done, current)

        return Reactive(CollectedIter(False, []), updates())

    @staticmethod
    def from_awaitable[V](awaitable: Awaitable[V]) -> Reactive[Maybe[V]]:
        async def updates() -> AsyncIterator[Maybe[V]]:
            result = await awaitable
            yield Maybe.some(result)

        return Reactive(Maybe.none(), updates())

    def map[R](self, fn: Callable[[T], R]) -> Reactive[R]:
        async def updates() -> AsyncIterator[R]:
            async for new_value in self.updates:
                yield fn(new_value)

        return Reactive(fn(self.initial), updates())

    def flat_map[R](self, fn: Callable[[T], Reactive[R]]) -> Reactive[R]:
        queue = asyncio.Queue[Maybe[R]]()
        initial_rx = fn(self.initial)

        async def put_all(values: AsyncIterator[R]) -> None:
            async for value in values:
                await queue.put(Maybe.some(value))

        async def watch_rx() -> None:
            async with asyncio.TaskGroup() as task_group:
                task = task_group.create_task(put_all(initial_rx.updates))
                async for new_value in self.updates:
                    new_rx = fn(new_value)
                    task.cancel()
                    await queue.put(Maybe.some(new_rx.initial))
                    task = task_group.create_task(put_all(new_rx.updates))
            await queue.put(Maybe.none())

        async def updates() -> AsyncIterator[R]:
            async with asyncio.TaskGroup() as task_group:
                task_group.create_task(watch_rx())
                while True:
                    item = await queue.get()
                    if item.is_some:
                        yield item.value
                    else:
                        break

        return Reactive(initial_rx.initial, updates())
