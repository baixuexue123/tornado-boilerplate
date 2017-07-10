import os
import logging
import logging.handlers

import tornado
import tornado.template
import tornado.options
from tornado.options import define, options

SECRET_KEY = 'django.boilerplate'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
TEMPLATE_ROOT = os.path.join(BASE_DIR, 'templates')

settings = dict(
    debug=True,
    static_root=STATIC_ROOT,
    cookie_secret='your-cookie-secret',
    xsrf_cookies=True,
    template_loader=tornado.template.Loader(TEMPLATE_ROOT)
)
