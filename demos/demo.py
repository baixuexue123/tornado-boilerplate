#!/usr/bin/env python
import tornado.web
import tornado.escape
import tornado.ioloop
import tornado.httpserver
from tornado import gen
from tornado.options import define, options, parse_command_line


class IndexHandler1(tornado.web.RequestHandler):
    def get(self):
        self.write("<p>Hello World</p>")


class IndexHandler2(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        self.write("<p>Hello</p>")
        self.write("<p>World</p>")
        yield gen.sleep(1.0)


class IndexHandler3(tornado.web.RequestHandler):
    @gen.coroutine
    def add(self, a, b):
        print('--- add ---')
        val = a + b
        return val

    @gen.coroutine
    def div(self, a, b):
        print('--- div ---')
        val = a / b
        return val

    @gen.coroutine
    def get(self):
        self.write("<p>Result:</p>")
        val = yield self.add(10, 11)
        self.write(str(val))

        self.write("<p>Result:</p>")
        val = yield self.div(1, 2)
        self.write(str(val))


settings = dict(
    debug=True
)

url_patterns = [
    (r"/index1", IndexHandler1),
    (r"/index2", IndexHandler2),
    (r"/index3", IndexHandler3),
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
