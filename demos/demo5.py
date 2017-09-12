#!/usr/bin/env python
import tornado.ioloop
from tornado import gen

import time


@gen.coroutine
def asyn_div(a, b):
    print(f"--- begin: div {a}+{b} ---")
    val = a / b
    return val


@gen.coroutine
def asyn_sum(a, b):
    print(f"--- begin: sum {a}+{b} ---")

    _sum = a + b

    _div = yield asyn_div(_sum, b)

    print("--- after yielded ---")
    print(f"end: sum:{_sum} div:{_div}")


def main():
    print('----------------------------')
    future = asyn_sum(1, 2)
    print('----------------------------')
    # tornado.ioloop.IOLoop.current().add_future(future, lambda f: f.result())
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
