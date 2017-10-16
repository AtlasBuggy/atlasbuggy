"""Example to cancel a set of asyncio coroutines (futures),
using one coroutine to signal the event loop to stop.
"""

import time
import signal
import asyncio
import logging
import threading
from concurrent.futures import CancelledError

logging.basicConfig(level=logging.DEBUG)


@asyncio.coroutine
def poll(incr=1.0):
    """A continuous coroutine."""
    i = 0
    while async_signal:
        print("Polling at {} seconds.".format(i))
        i += incr
        yield from asyncio.sleep(incr)


threaded_shutdown_signal = True
async_signal = True

@asyncio.coroutine
def thread_poll():
    """A continuous coroutine."""

    def thread_loop():
        while threaded_shutdown_signal:
            print("Thread is running")
            time.sleep(1)

    nonstopping_thread = threading.Thread(target=thread_loop)
    nonstopping_thread.daemon = True
    nonstopping_thread.start()

    while True:
        print("Polling at 1.0 seconds.")
        yield from asyncio.sleep(1.0)


@asyncio.coroutine
def stop(duration):
    """The coroutine to listen for signal to stop the event loop."""
    # In practice, a signal of sorts (e.g., through a TCP socket) may
    # be send here to indicate a full stop
    yield from asyncio.sleep(duration)
    # Alternatively, one can raise an Exception and use
    # `return_when=asyncio.FIRST_EXCEPTION` in `asyncio.wait`.


def teardown(loop):
    # global async_signal
    # async_signal = False
    # print("from here I will wait until connection_with_client has finished")
    # tasks[0].add_done_callback(lambda _: loop.stop())
    # tasks[1].add_done_callback(lambda _: loop.stop())
    for task in tasks:
        logging.info("Cancelling %s: %s" % (task, task.cancel()))

tasks = []


def main():
    global threaded_shutdown_signal
    loop = asyncio.get_event_loop()
    # For Python 3.4.4, use `ensure_future` instead of `async` below
    tasks.extend([
        asyncio.async(poll(2)),
        asyncio.async(poll(1.4)),
        asyncio.async(stop(5)),
        asyncio.async(thread_poll())
    ])
    loop.add_signal_handler(signal.SIGINT, teardown, loop)
    finished, pending = loop.run_until_complete(
        asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED))
    # logging.debug(">> Finished: %s" % finished)
    # logging.debug(">> Pending: %s" % pending)
    # # Cancel the remaining tasks
    # for task in pending:
    #     logging.info("Cancelling %s: %s" % (task, task.cancel()))
    # try:
    #     loop.run_until_complete(asyncio.gather(*pending))
    # except CancelledError:  # Any other exception would be bad
    #     for task in pending:
    #         logging.debug("Cancelled %s: %s" % (task, task.cancelled()))
    # Stop and clean up
    # threaded_shutdown_signal = False
    # loop.stop()
    # loop.close()


if __name__ == "__main__":
    main()
