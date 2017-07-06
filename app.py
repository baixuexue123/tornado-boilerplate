#! /usr/bin/env python
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.options import options

from .settings import settings
from .urls import url_patterns


class TornadoBoilerplate(tornado.web.Application):
    def __init__(self):
        tornado.web.Application.__init__(self, url_patterns, **settings)


def main():
    app = TornadoBoilerplate()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(options.port)
    server.start(0)  # forks one process per cpu
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
