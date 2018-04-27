import os
import logging
import logging.handlers

import redis

import tornado
import tornado.template
import tornado.options
from tornado.options import define, options

SECRET_KEY = 'tornado.app'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
TEMPLATE_ROOT = os.path.join(BASE_DIR, 'templates')

settings = dict(
    title="Tornado server",
    debug=True,
    static_root=STATIC_ROOT,
    cookie_secret='your-cookie-secret',
    xsrf_cookies=True,
    login_url="/auth/login",
    template_path=TEMPLATE_ROOT,
    template_loader=tornado.template.Loader(TEMPLATE_ROOT),
)

settings['session'] = dict(
    session_id_name='token',
    expire_seconds=60 * 60 * 1,
    backend=redis.StrictRedis(host='127.0.0.1', port=6379, db=0),
)

settings['database'] = dict(
    host='127.0.0.1',
    db='db',
    user='user',
    password='***',
)

settings['media'] = dict(
    root='/opt/media/crm/',
    url='/media/',
)
