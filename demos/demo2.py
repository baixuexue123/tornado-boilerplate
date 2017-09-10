#!/usr/bin/env python
import time

import tornado.web
import tornado.escape
import tornado.ioloop
import tornado.httpserver
from tornado import gen
from tornado.options import define, options, parse_command_line
from tornado.log import app_log

import tcelery
from . import tasks

tcelery.setup_nonblocking_producer()


class AsyncHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        tasks.sleep.apply_async(args=[3], callback=self.on_result)

    def on_result(self, response):
        self.write(str(response.result))
        self.finish()


class GenAsyncHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        response = yield gen.Task(tasks.sleep.apply_async, args=[3])
        self.write(str(response.result))
        self.finish()


class GenMultipleAsyncHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        r1, r2 = yield [gen.Task(tasks.sleep.apply_async, args=[2]),
                        gen.Task(tasks.add.apply_async, args=[1, 2])]
        self.write(str(r1.result))
        self.write(str(r2.result))
        self.finish()


settings = dict(
    debug=True
)

url_patterns = [
    (r"/async-sleep", AsyncHandler),
    (r"/gen-async-sleep", GenAsyncHandler),
    (r"/gen-async-sleep-add", GenMultipleAsyncHandler),
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
