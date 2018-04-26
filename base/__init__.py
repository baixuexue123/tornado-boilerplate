import sys
import functools
import concurrent.futures

import bcrypt
import lazy_object_proxy

import tornado.web
from tornado.web import HTTPError, Finish
from tornado import httputil
from tornado.concurrent import run_on_executor
from tornado.log import app_log, gen_log

from contrib import torndb
from contrib.session import Session, InvalidSesssionID
from utils import cached_property
from utils.text import force_bytes
from utils.mail import send_mail


def permission_required(permisions=None, raise_exception=True):
    """Decorate methods with this to require permisions
    """
    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            if self.permission_required is None:
                perms = []
            elif isinstance(self.permission_required, str):
                perms = [self.permission_required]
            elif isinstance(self.permission_required, (list, tuple)):
                perms = list(self.permission_required)
            else:
                raise ValueError('permission_required must be str, list, tuple')

            if permisions is not None:
                if isinstance(permisions, str):
                    perms.append(permisions)
                elif isinstance(permisions, (list, tuple)):
                    perms.extend(permisions)
                else:
                    raise ValueError('permisions must be str, list, tuple')

            if perms:
                has_perm = functools.partial(self.has_perm, raise_exception=raise_exception)
                if not all(map(has_perm, perms)):
                    raise HTTPError(status_code=403, log_message='PermissionDenied')
            return method(self, *args, **kwargs)
        return wrapper
    return decorator


class SessionError(Exception):
    """ 请求缺少session id """
    pass


class BaseHandler(tornado.web.RequestHandler):

    executor = concurrent.futures.ThreadPoolExecutor(2)
    permission_required = None

    def initialize(self):
        _db = self.settings['database']
        self.db = torndb.Connection(
            host=_db['host'], database=_db['db'],
            user=_db['user'], password=_db['password']
        )

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST,GET,PUT,DELETE')

    def _get_session_id(self):
        return self.get_cookie(self.settings['session']['session_id_name'])

    def new_session(self):
        setattr(self, '__session_manager', Session(self.settings['session']))

    def invalidate_session(self, session_id):
        backend = self.settings['session']['backend']
        backend.delete(session_id)

    @property
    def session(self):
        """ Returns a Session instance """
        if not hasattr(self, '__session_manager'):
            sid = self._get_session_id()
            if sid is None:
                raise SessionError("缺少%s" % self.settings['session']['session_id_name'])
            setattr(self, '__session_manager', Session(self.settings['session'], sid))
        return getattr(self, '__session_manager')

    def _handle_request_exception(self, e):
        if isinstance(e, Finish):
            # Not an error; just finish the request without logging.
            if not self._finished:
                self.finish(*e.args)
            return
        elif isinstance(e, (SessionError, InvalidSesssionID)):
            self.redirect(self.get_login_url())
        try:
            self.log_exception(*sys.exc_info())
        except Exception:
            # An error here should still get a best-effort send_error()
            # to avoid leaking the connection.
            app_log.error("Error in exception logger", exc_info=True)
        if self._finished:
            # Extra errors after the request has been finished should
            # be logged, but there is no reason to continue to try and
            # send a response.
            return
        if isinstance(e, HTTPError):
            if e.status_code not in httputil.responses and not e.reason:
                gen_log.error("Bad HTTP status code: %d", e.status_code)
                self.send_error(500, exc_info=sys.exc_info())
            else:
                self.send_error(e.status_code, exc_info=sys.exc_info())
        else:
            self.send_error(500, exc_info=sys.exc_info())

    def get_login_url(self):
        return self.reverse_url('login')

    def get_current_user(self):
        user_id = self.get_secure_cookie('userId')
        if not user_id:
            return
        user = self.get_user(id=user_id)
        if not user:
            return

        _role_proxy = functools.partial(self.get_role, role_id=user['role_id'])
        _regions_proxy = functools.partial(self.get_user_regions, user_id=user_id)
        _businesses_proxy = functools.partial(self.get_user_businesses, user_id=user_id)
        _groups_proxy = functools.partial(self.get_user_groups, user_id=user_id)
        user['role'] = lazy_object_proxy.Proxy(_role_proxy)
        user['regions'] = lazy_object_proxy.Proxy(_regions_proxy)
        user['businesses'] = lazy_object_proxy.Proxy(_businesses_proxy)
        user['groups'] = lazy_object_proxy.Proxy(_groups_proxy)
        return user

    @run_on_executor
    def hashpw(self, password):
        return bcrypt.hashpw(force_bytes(password), bcrypt.gensalt())

    @run_on_executor
    def checkpw(self, password, hashed_pw):
        return bcrypt.checkpw(force_bytes(password), force_bytes(hashed_pw))

    def delay(self, method, *args, **kwargs):
        return self.executor.submit(functools.partial(method, *args, **kwargs))

    def send_mail(self, receivers, body, subject='CRM系统邮件'):
        self.delay(send_mail, receivers, subject, body)

    def on_finish(self):
        self.db.close()
        if hasattr(self, '__session_manager'):
            self.session.save()


class ExportBase(BaseHandler):

    def get_current_user(self):
        try:
            user_id = self.session['userId']
        except KeyError:
            return
        user = self.get_user(id=user_id)
        if not user:
            return

        _role_proxy = functools.partial(self.get_role, role_id=user['role_id'])
        _regions_proxy = functools.partial(self.get_user_regions, user_id=user_id)
        _groups_proxy = functools.partial(self.get_user_groups, user_id=user_id)
        user['role'] = lazy_object_proxy.Proxy(_role_proxy)
        user['regions'] = lazy_object_proxy.Proxy(_regions_proxy)
        user['groups'] = lazy_object_proxy.Proxy(_groups_proxy)
        return user

    def prepare(self):
        """认证用户是否登录
        用@tornado.web.authenticated修饰器做登录认证
        会重定向到admin的登录页, 这里只需要返回401
        """
        if not self.current_user:
            self.send_error(401)

    def _handle_request_exception(self, e):
        if isinstance(e, Finish):
            # Not an error; just finish the request without logging.
            if not self._finished:
                self.finish(*e.args)
            return
        elif isinstance(e, (SessionError, InvalidSesssionID)):
            self.send_error(403, exc_info=sys.exc_info())
            return
        try:
            self.log_exception(*sys.exc_info())
        except Exception:
            # An error here should still get a best-effort send_error()
            # to avoid leaking the connection.
            app_log.error("Error in exception logger", exc_info=True)
        if self._finished:
            # Extra errors after the request has been finished should
            # be logged, but there is no reason to continue to try and
            # send a response.
            return
        if isinstance(e, HTTPError):
            if e.status_code not in httputil.responses and not e.reason:
                gen_log.error("Bad HTTP status code: %d", e.status_code)
                self.send_error(500, exc_info=sys.exc_info())
            else:
                self.send_error(e.status_code, exc_info=sys.exc_info())
        else:
            self.send_error(500, exc_info=sys.exc_info())
