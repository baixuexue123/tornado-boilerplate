import logging
from pprint import pprint

import tornado.web
import tornado.escape
import tornado.ioloop
import tornado.httpserver
from tornado import gen
from tornado.options import define, options, parse_command_line

from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

from contrib.torndb import Connection

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)


DB_CONNECT_STRING = 'mysql+pymysql://crm:123@localhost:3306/employees'
engine = create_engine(DB_CONNECT_STRING, encoding='utf-8', echo=True,
                       pool_size=5, max_overflow=10, poolclass=QueuePool,
                       pool_recycle=3600*6)


def getconn():
    return Connection(host='127.0.0.1', database='employees', user='crm', password='123')


class IndexHandler1(tornado.web.RequestHandler):

    pool = QueuePool(getconn, max_overflow=10, pool_size=5)

    @gen.coroutine
    def get(self):
        conn = self.pool.connect()
        pprint(conn.query("SELECT COUNT(*) FROM departments"))

        pprint(self.pool.status())

        self.write("<p>Hello World</p>")


class IndexHandler2(tornado.web.RequestHandler):

    def initialize(self):
        self.db = Connection(host='127.0.0.1', database='employees', user='crm', password='123')

    @gen.coroutine
    def get(self):
        pprint(self.db.query("SELECT COUNT(*) FROM departments"))
        self.write("<p>Hello World</p>")

    def on_finish(self):
        self.db.close()


settings = dict(
    debug=True
)

url_patterns = [
    (r"/index1", IndexHandler1),
    (r"/index2", IndexHandler2),
]


def make_app():
    return tornado.web.Application(
        url_patterns, **settings
    )


def main():
    define("port", default=8000, help="run on the given port", type=int)
    parse_command_line()

    app = make_app()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
