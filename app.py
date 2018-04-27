#! /usr/bin/env python
import tornado.httpserver
import tornado.web
import tornado.options
from tornado.ioloop import IOLoop
from tornado.options import define, options

from .settings import settings
from .urls import url_patterns

define("bind", default='127.0.0.1', help="bind address", type=str)
define("port", default=8888, help="run on the given port", type=int)
define("debug", default=False, help="debug mode", type=bool)


class Application(tornado.web.Application):
    def __init__(self):
        tornado.web.Application.__init__(self, url_patterns, **settings)


def main():
    tornado.options.parse_command_line()

    app = Application()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(options.port, address='127.0.0.1')
    IOLoop.current().start()


if __name__ == "__main__":
    main()
