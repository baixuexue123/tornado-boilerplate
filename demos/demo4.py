from urllib.request import urlopen

from tornado import gen
from tornado.gen import Future
from tornado.ioloop import IOLoop


@gen.coroutine
def handle_response(resp):
    print(resp)
    return resp


@gen.coroutine
def fetch(url):
    print('fetch: 1111111111111111')
    resp = urlopen(url)
    print('fetch: 2222222222222222')
    resp = yield handle_response(resp)
    return resp


if __name__ == '__main__':
    print('start')

    future = fetch('http://python.jobbole.com/')

    print('end')
    io_loop = IOLoop.current()
    io_loop.add_future(future, lambda f: io_loop.stop())
    io_loop.start()
