from handlers.base import BaseHandler

import logging

logger = logging.getLogger('boilerplate.' + __name__)

access_log = logging.getLogger("tornado.access")
app_log = logging.getLogger("tornado.application")
gen_log = logging.getLogger("tornado.general")


class FooHandler(BaseHandler):
    def get(self):
        self.render("base.html")
