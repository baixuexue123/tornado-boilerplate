import tornado.web
from tornado import gen


class IndexHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        self.render("base.html")
