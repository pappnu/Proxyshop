from asyncio import EventLoop, get_running_loop, run
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any

_thread_pool = ThreadPoolExecutor(max_workers=4)


def async_to_sync[T](awaitable: Coroutine[Any, Any, T]) -> T:
    return _thread_pool.submit(run, awaitable, loop_factory=EventLoop).result()


async def run_in_thread[T](coro: Coroutine[Any, Any, T]) -> None:
    def target():
        # Using asyncio.run without a factory starts another Qt loop, since
        # Qt sets the global loop policy to it's own implementation.
        # Starting another Qt loop fails, because the loop also tries to
        # exec another Qt application. As a workaround, we have to specifically
        # create an instance of the default non-Qt event loop.
        run(coro, loop_factory=EventLoop)

    get_running_loop().run_in_executor(_thread_pool, target)
