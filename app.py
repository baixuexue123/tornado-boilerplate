#! /usr/bin/env python
import os.path

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.options
from tornado.options import define, options

from .settings import settings
from .urls import url_patterns


define("port", default=8888, help="Run on the given port", type=int)
define("debug", default=False, help="Debug mode", type=bool)

tornado.options.parse_command_line()

options['log_file_prefix'] = os.path.join(settings.BASE_DIR, 'logs/boilerplate@8001.log')
options['logging'] = 'debug' if options.debug else 'info'


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
