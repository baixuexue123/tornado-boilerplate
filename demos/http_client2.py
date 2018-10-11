from tornado import gen
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.httpclient import AsyncHTTPClient


@gen.coroutine
def fetch(urls):
    http = AsyncHTTPClient()
    resp = yield list(map(http.fetch, urls))
    return resp


if __name__ == '__main__':
    import pprint
    urls = [
        'http://python.jobbole.com/',
        'http://www.baidu.com/',
        'http://www.sohu.com/',
        'http://www.sina.com/',
        'http://www.ruanyifeng.com',
        'http://cnodejs.org/',
        'http://www.pythontab.com/',
        'http://docs.jinkan.org/docs/jinja2/',
        'https://www.djangoproject.com/start/overview/',
        'http://www.semantic-ui.cn/',
    ]
    future = fetch(urls)

    io_loop = IOLoop.current()
    io_loop.add_future(future, lambda f: io_loop.stop())

    def callback():
        pprint.pprint(io_loop._handlers)

    period = PeriodicCallback(callback=callback, callback_time=200, io_loop=io_loop)
    period.start()

    io_loop.start()
