from tornado import gen
from tornado.ioloop import IOLoop
from tornado.tcpserver import TCPServer
from tornado.iostream import StreamClosedError
from tornado.options import define, options, parse_command_line


class EchoServer(TCPServer):
    @gen.coroutine
    def handle_stream(self, stream, address):
        while True:
            try:
                data = yield stream.read_until(b"\n")
                yield stream.write(data)
            except StreamClosedError:
                break


def main():
    define("port", default=8000, help="run on the given port", type=int)
    parse_command_line()

    server = TCPServer()
    server.listen(options.port)
    IOLoop.current().start()


if __name__ == "__main__":
    main()
