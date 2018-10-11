import errno
import functools
import socket
import tornado.ioloop


def handle_connection(connection, address):
    pass


def connection_ready(sock, fd, events):
    while True:
        try:
            connection, address = sock.accept()
        except socket.error as e:
            if e.args[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
                raise
            return
        connection.setblocking(0)

        handle_connection(connection, address)


if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setblocking(0)
    sock.bind(("127.0.0.1", 8000))
    sock.listen(128)

    ioloop = tornado.ioloop.IOLoop.current()
    callback = functools.partial(connection_ready, sock)
    ioloop.add_handler(sock.fileno(), callback, ioloop.READ)
    ioloop.start()
