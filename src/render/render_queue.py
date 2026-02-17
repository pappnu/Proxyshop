from asyncio import EventLoop, Future, Task, run
from logging import getLogger
from threading import Lock, Thread
from typing import TypedDict

from src.render.setup import RenderOperation
from src.utils.event import SubscribableEvent

_logger = getLogger(__name__)


class RenderResult(TypedDict):
    operation: RenderOperation
    result: bool


class RenderQueue:
    """Queue for render operations. Runs the render loop in a separate thread."""

    _render_lock = Lock()

    def __init__(self) -> None:
        self._queue: list[RenderOperation] = []
        self._queue_lock = Lock()

        self._active_operation: RenderOperation | None = None
        self._cancel: bool = False

        self.queued: SubscribableEvent[tuple[RenderOperation, ...]] = (
            SubscribableEvent()
        )
        self.dequeued: SubscribableEvent[tuple[RenderOperation, int]] = (
            SubscribableEvent()
        )
        self.started: SubscribableEvent[RenderOperation] = SubscribableEvent()
        self.finished: SubscribableEvent[RenderResult] = SubscribableEvent()
        self.cancelled: SubscribableEvent[None] = SubscribableEvent()

    @property
    def active_operation(self) -> RenderOperation | None:
        return self._active_operation

    def enqueue(self, *operations: RenderOperation) -> None:
        with self._queue_lock:
            self._queue.extend(operations)
        self.queued.trigger(operations)
        self.execute_render()

    def dequeue(self, index: int) -> RenderOperation | None:
        try:
            with self._queue_lock:
                self.dequeued.trigger((self._queue.pop(index), index))
        except IndexError:
            return

    def clear(self) -> None:
        with self._queue_lock:
            for idx in reversed(range(len(self._queue))):
                self.dequeued.trigger((self._queue.pop(), idx))

    def cancel(self) -> None:
        if self._active_operation:
            self._cancel = True
            self._active_operation.cancel()
            self.cancelled.trigger(None)

    def execute_render(self) -> None:
        if self._render_lock.locked():
            return

        async def loop_render():
            locked = self._render_lock.acquire(blocking=False)
            if locked:
                try:
                    try:
                        while not self._cancel and (next_render := self._queue.pop(0)):
                            self._active_operation = next_render
                            self.started.trigger(next_render)
                            result = False
                            try:
                                result = await next_render.render()
                            finally:
                                self.finished.trigger(
                                    {"operation": next_render, "result": result}
                                )
                    except IndexError:
                        return
                    finally:
                        self._active_operation = None
                        self._cancel = False
                finally:
                    self._render_lock.release()

        def target():
            # Using asyncio.run without a factory starts another Qt loop, since
            # Qt sets the global loop policy to it's own implementation.
            # Starting another Qt loop fails, because the loop also tries to
            # exec another Qt application. As a workaround, we have to specifically
            # create an instance of the default non-Qt event loop.
            run(loop_render(), loop_factory=EventLoop)

        Thread(target=target).start()


def cancel_with_render[T](
    task: Future[T] | Task[T], queue: RenderQueue, msg: str | None = None
) -> None:
    def on_cancel(_: None = None) -> None:
        task.cancel()

    queue.cancelled.listen_once(on_cancel)
    task.add_done_callback(lambda _: queue.cancelled.remove_listener(on_cancel))
