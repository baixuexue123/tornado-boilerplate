#!/usr/bin/env python
import time
from concurrent.futures import ThreadPoolExecutor

import tornado.web
import tornado.escape
import tornado.ioloop
import tornado.httpserver
from tornado import gen
from tornado.concurrent import Future, run_on_executor
from tornado.options import define, options, parse_command_line
from tornado.log import app_log


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
