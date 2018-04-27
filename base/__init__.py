import sys
import functools
import concurrent.futures

import bcrypt
import lazy_object_proxy
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

import tornado.web
import tornado.escape
from tornado.web import HTTPError, Finish
from tornado import httputil
from tornado.concurrent import run_on_executor
from tornado.log import app_log, gen_log

from contrib import torndb
from contrib.session import Session, InvalidSesssionID
from utils.text import force_bytes


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

    @property
    def db(self):
        """ Returns a DB-API instance """
        if not hasattr(self, '__db'):
            _db = self.settings['database']
            db = torndb.Connection(
                host=_db['host'], database=_db['db'],
                user=_db['user'], password=_db['password']
            )
            setattr(self, '__db', db)
        return getattr(self, '__db')

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

    def get_user(self, user_id):
        return {}

    def get_user_profile(self, user_id):
        return {}

    def get_current_user(self):
        user_id = self.get_secure_cookie('userId')
        if not user_id:
            return
        user = self.get_user(user_id)
        if not user:
            return

        _proxy = functools.partial(self.get_user_profile, user_id)
        user['profile'] = lazy_object_proxy.Proxy(_proxy)
        return user

    @run_on_executor
    def hashpw(self, password):
        return bcrypt.hashpw(force_bytes(password), bcrypt.gensalt())

    @run_on_executor
    def checkpw(self, password, hashed_pw):
        return bcrypt.checkpw(force_bytes(password), force_bytes(hashed_pw))

    def delay(self, method, *args, **kwargs):
        return self.executor.submit(functools.partial(method, *args, **kwargs))

    def on_finish(self):
        if hasattr(self, '__db'):
            self.db.close()
        if hasattr(self, '__session_manager'):
            self.session.save()


class Jinja2Handler(BaseHandler):

    def render_template(self, template_name, **kwargs):
        template_dirs = []
        if self.settings.get('template_path', ''):
            template_dirs.append(
                self.settings["template_path"]
            )

        env = Environment(loader=FileSystemLoader(template_dirs))

        try:
            template = env.get_template(template_name)
        except TemplateNotFound:
            raise TemplateNotFound(template_name)
        content = template.render(kwargs)
        return content

    def render(self, template_name, **kwargs):
        """
        This is for making some extra context variables available to
        the template
        """
        kwargs.update({
            'handler': self,
            'settings': self.settings,
            'STATIC_URL': self.settings.get('static_url_prefix', '/static/'),
            'static_url': self.static_url,
            'reverse_url': self.reverse_url,
            'request': self.request,
            'xsrf_token': self.xsrf_token,
            'current_user': self.current_user,
            'xsrf_form_html': self.xsrf_form_html,
        })
        content = self.render_template(template_name, **kwargs)
        self.write(content)


class ApiHandler(BaseHandler):

    SUPPORTED_METHODS = ("GET", "POST", "DELETE", "PUT")

    def _get_session_id(self):
        session_id = self.get_cookie(self.settings['session']['session_id_name'])
        if session_id is not None:
            return session_id
        if self.request.method == 'GET':
            return self.get_query_argument(self.settings['session']['session_id_name'], None)
        elif self.request.method in ('POST', 'PUT', 'DELETE'):
            return self.get_json_argument(self.settings['session']['session_id_name'], None)

    def success(self, code=0, message='', **kwargs):
        self.write({
            'code': code,
            'message': message,
            'data': kwargs,
        })

    def failure(self, code=1, message='', **kwargs):
        self.write({
            'code': code,
            'message': message,
            'data': kwargs,
        })

    def _handle_request_exception(self, e):
        if isinstance(e, Finish):
            # Not an error; just finish the request without logging.
            if not self._finished:
                self.finish(*e.args)
            return
        elif isinstance(e, SessionError):
            self.failure(code=11000, message="缺少%s" % self.settings['session']['session_id_name'])
            self.finish()
            return
        elif isinstance(e, InvalidSesssionID):
            self.failure(code=12000, message="无效的%s" % self.settings['session']['session_id_name'])
            self.finish()
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

    def write_error(self, status_code, **kwargs):
        """Override to implement custom error pages.

        ``write_error`` may call `write`, `render`, `set_header`, etc
        to produce output as usual.

        If this error was caused by an uncaught exception (including
        HTTPError), an ``exc_info`` triple will be available as
        ``kwargs["exc_info"]``.  Note that this exception may not be
        the "current" exception for purposes of methods like
        ``sys.exc_info()`` or ``traceback.format_exc``.
        """
        self.failure(code=status_code, message=self._reason)

    _ARG_DEFAULT = tornado.web.RequestHandler._ARG_DEFAULT

    def get_json_argument(self, name, default=_ARG_DEFAULT):
        """Find and return the argument with key 'name' from JSON request data.
        Similar to Tornado's get_argument() method.
        """
        if name not in self.request.body_arguments:
            if default is self._ARG_DEFAULT:
                msg = "Missing argument '%s'" % name
                app_log.debug(msg)
                raise tornado.web.HTTPError(400, msg)
            else:
                return default
        return self.request.body_arguments[name]

    def prepare(self):
        if self.request.headers.get("Content-Type", "").startswith("application/json"):
            # If JSON cannot be decoded, raises an HTTPError with status 400.
            try:
                self.request.body_arguments = tornado.escape.json_decode(self.request.body)
            except ValueError:
                msg = "Could not decode JSON: %s" % self.request.body
                raise tornado.web.HTTPError(400, msg)
