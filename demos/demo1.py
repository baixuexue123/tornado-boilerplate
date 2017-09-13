#!/usr/bin/env python
import time
from concurrent.futures import ThreadPoolExecutor

import tornado.web
import tornado.escape
import tornado.ioloop
import tornado.httpserver
from tornado import gen
from tornado.concurrent import Future, run_on_executor
from tornado.httpclient import AsyncHTTPClient
from tornado.options import define, options, parse_command_line
from tornado.log import app_log


class IndexBadHandler(tornado.web.RequestHandler):
    """
    asynchronous装饰器是让请求变成长连接的方式,
    必须手动调用 self.finish() 才会响应,
    如果没有指定结束, 该长连接会一直保持直到 pending 状态.
    """
    @tornado.web.asynchronous
    def get(self):
        self.write("<p>Hello, world</p>")


class IndexGoodHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.write("<p>Hello, world</p>")
        self.finish()


class AsyncHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        http_client = AsyncHTTPClient()
        http_client.fetch("http://example.com",
                          callback=self.on_fetch)

    def on_fetch(self, response):
        # do_something_with_response(response)
        self.render("template.html")


class GenAsyncHandler1(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        http_client = AsyncHTTPClient()
        response = yield http_client.fetch("http://example.com")
        # do_something_with_response(response)
        self.render("template.html")


class GenAsyncHandler2(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        http_client = AsyncHTTPClient()
        url1, url2, url3, url4 = ['http://example.com',
                                  'http://example.com',
                                  'http://example.com',
                                  'http://example.com']

        response1, response2 = yield [http_client.fetch(url1),
                                      http_client.fetch(url2)]

        response_dict = yield dict(response3=http_client.fetch(url3),
                                   response4=http_client.fetch(url4))
        response3 = response_dict['response3']
        response4 = response_dict['response4']


class GenAsyncHandler3(tornado.web.RequestHandler):
    @gen.coroutine
    def add(self, a, b):
        val = a + b
        yield gen.sleep(2.0)
        return val

    @gen.coroutine
    def get(self):
        a = self.get_query_argument('a', 0)
        b = self.get_query_argument('b', 0)
        self.write("<p>Result:</p>")
        val = yield self.add(a, b)
        self.write(str(val))


class NoBlockingHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        yield gen.sleep(10)
        self.write('<p>No Blocking Request</p>')


class BlockingHandler(tornado.web.RequestHandler):
    def get(self):
        time.sleep(10)
        self.write('<p>Blocking Request</p>')


class NoBlockingThreadHandler(tornado.web.RequestHandler):
    executor = ThreadPoolExecutor(2)

    @run_on_executor
    def sleep(self, seconds):
        time.sleep(seconds)
        return seconds

    @gen.coroutine
    def get(self):
        second = yield self.sleep(5)
        self.write(f'noBlocking Request: {second}')


settings = dict(
    debug=True
)

url_patterns = [
    (r"/bad", IndexBadHandler),
    (r"/good", IndexGoodHandler),
    (r"/async", AsyncHandler),
    (r"/coroutine1", GenAsyncHandler1),
    (r"/coroutine2", GenAsyncHandler2),
    (r"/coroutine3", GenAsyncHandler3),
    (r"/noblocking", NoBlockingHandler),
    (r"/blocking", BlockingHandler),
    (r"/noblockingthread", NoBlockingThreadHandler),
]


class Application(tornado.web.Application):
    def __init__(self):
        super(Application, self).__init__(url_patterns, **settings)


def main():
    define("port", default=8000, help="run on the given port", type=int)
    parse_command_line()

    app = Application()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
