#!/usr/bin/env python
import pprint

import tornado.web
import tornado.gen
import tornado.escape
import tornado.ioloop
import tornado.httpserver
from tornado.options import define, options, parse_command_line


def handle_request(request):
    message = "<p>Got it: %s</p>" % request.full_url()
    length = len(message)
    request.write(tornado.escape.utf8(f"HTTP/1.1 200 OK\r\nContent-Length: {length}\r\n\r\n{message}"))
    request.finish()


def main():
    define("port", default=8000, help="Run on the given port", type=int)
    parse_command_line()

    server = tornado.httpserver.HTTPServer(handle_request)
    server.listen(options.port, address='127.0.0.1')

    pprint.pprint(server.io_loop._handlers)

    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
