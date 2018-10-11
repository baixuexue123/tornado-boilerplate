import tornado.ioloop
from tornado import gen

import time


@gen.coroutine
def asyn_div(a, b):
    print("22222222222222222222")
    val = a / b
    yield gen.sleep(2.0)
    print("3333333333333333333")
    return val


@gen.coroutine
def asyn_sum(a, b):
    print("1111111111111111111")

    _sum = a + b

    _div = yield asyn_div(_sum, b)

    print(_div)
    print("4444444444444444444")


def main():
    print('------------ begin ----------------')
    future = asyn_sum(1, 2)
    print('------------- end ---------------')
    io_loop = tornado.ioloop.IOLoop.current()
    io_loop.add_future(future, lambda f: io_loop.stop())
    io_loop.start()


if __name__ == "__main__":
    main()
