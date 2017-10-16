import time
import asyncio
from concurrent.futures import ProcessPoolExecutor

print('running async test')


def say_something():
    i = 0
    t0 = time.time()
    while True:
        print('...something %s, %0.4f' % (i, time.time() - t0))
        i += 1
        time.sleep(1)


def say_else():
    i = 0
    t0 = time.time()
    while True:
        print('...else %s, %0.4f' % (i, time.time() - t0))
        i += 1
        time.sleep(1)


if __name__ == "__main__":
    executor = ProcessPoolExecutor(2)
    loop = asyncio.get_event_loop()
    something = asyncio.ensure_future(loop.run_in_executor(executor, say_something))
    _else = asyncio.ensure_future(loop.run_in_executor(executor, say_else))

    loop.run_forever()
