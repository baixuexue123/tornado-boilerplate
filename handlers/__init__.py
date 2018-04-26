import sys
import time
import functools
import lazy_object_proxy

import tornado.web
import tornado.escape
from tornado import httputil
from tornado.concurrent import Future
from tornado.web import HTTPError, Finish
from tornado.log import app_log, gen_log

from contrib.session import InvalidSesssionID
from base import BaseHandler, SessionError
from utils.escape import json_encode


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

    def get_current_user(self):
        try:
            user_id = self.session['userId']
        except KeyError:
            return None

        user = self.get_user(id=user_id)
        if user and user.is_active:
            _role_proxy = functools.partial(self.get_role, role_id=user['role_id'])
            _regions_proxy = functools.partial(self.get_user_regions, user_id=user_id)
            _businesses_proxy = functools.partial(self.get_user_businesses, user_id=user_id)
            _groups_proxy = functools.partial(self.get_user_groups, user_id=user_id)
            user['role'] = lazy_object_proxy.Proxy(_role_proxy)
            user['regions'] = lazy_object_proxy.Proxy(_regions_proxy)
            user['businesses'] = lazy_object_proxy.Proxy(_businesses_proxy)
            user['groups'] = lazy_object_proxy.Proxy(_groups_proxy)
        return user

    def clear(self):
        """Resets all headers and content for this response."""
        self._headers = httputil.HTTPHeaders({
            "Content-Type": "application/json; charset=UTF-8",
            "Date": httputil.format_timestamp(time.time()),
        })
        self.set_default_headers()
        self._write_buffer = {}
        self._status_code = 200
        self._reason = httputil.responses[200]

    def write(self, chunk):
        """Writes the given chunk to the output buffer.

        To write the output to the network, use the flush() method below.
        """
        if self._finished:
            raise RuntimeError("Cannot write() after finish()")
        if isinstance(chunk, dict):
            self._write_buffer.update(chunk)
        else:
            # message = "write() only accepts dict objects"
            if 'Traceback' in self._write_buffer:
                self._write_buffer['Traceback'] += str(chunk)
            else:
                self._write_buffer['Traceback'] = str(chunk)

    def success(self, code=0, message='', token=None, **kwargs):
        """ 新API接口 """
        if self._finished:
            raise RuntimeError("Cannot write() after finish()")
        if token is not None:
            self._write_buffer['token'] = self.session.id
        self._write_buffer['code'] = code
        self._write_buffer['message'] = message
        self._write_buffer['data'] = kwargs

    def failure(self, code=1, message='', **kwargs):
        if self._finished:
            raise RuntimeError("Cannot write() after finish()")
        self._write_buffer['code'] = code
        self._write_buffer['message'] = message
        self._write_buffer['data'] = kwargs

    def flush(self, include_footers=False, callback=None,  chunk=None):
        """Flushes the current output buffer to the network.

        The ``callback`` argument, if given, can be used for flow control:
        it will be run when all flushed data has been written to the socket.
        Note that only one flush callback can be outstanding at a time;
        if another flush occurs before the previous flush's callback
        has been run, the previous callback will be discarded.
        """
        if chunk is None:
            chunk = json_encode(self._write_buffer)
            chunk = tornado.escape.utf8(chunk)

        self._write_buffer = {}

        if not self._headers_written:
            self._headers_written = True
            for transform in self._transforms:
                self._status_code, self._headers, chunk = \
                    transform.transform_first_chunk(
                        self._status_code, self._headers, chunk, include_footers)
            # Ignore the chunk and only write the headers for HEAD requests
            if self.request.method == "HEAD":
                chunk = None

            # Finalize the cookie headers (which have been stored in a side
            # object so an outgoing cookie could be overwritten before it
            # is sent).
            if hasattr(self, "_new_cookie"):
                for cookie in self._new_cookie.values():
                    self.add_header("Set-Cookie", cookie.OutputString(None))

            start_line = httputil.ResponseStartLine('', self._status_code, self._reason)
            return self.request.connection.write_headers(
                start_line, self._headers, chunk, callback=callback)
        else:
            for transform in self._transforms:
                chunk = transform.transform_chunk(chunk, include_footers)
            # Ignore the chunk and only write the headers for HEAD requests
            if self.request.method != "HEAD":
                return self.request.connection.write(chunk, callback=callback)
            else:
                future = Future()
                future.set_result(None)
                return future

    def finish(self, chunk=None):
        """Finishes this response, ending the HTTP request."""
        if self._finished:
            raise RuntimeError("finish() called twice")

        if chunk is not None:
            self.write(chunk)

        # Automatically support ETags and add the Content-Length header if
        # we have not flushed any content yet.
        if not self._headers_written:
            if self._status_code in (204, 304):
                assert not self._write_buffer, "Cannot send body with %s" % self._status_code
                self._clear_headers_for_304()
            elif "Content-Length" not in self._headers:
                chunk = json_encode(self._write_buffer)
                chunk = tornado.escape.utf8(chunk)
                self.set_header("Content-Length", len(chunk))

        if hasattr(self.request, "connection"):
            # Now that the request is finished, clear the callback we
            # set on the HTTPConnection (which would otherwise prevent the
            # garbage collection of the RequestHandler when there
            # are keepalive connections)
            self.request.connection.set_close_callback(None)

        self.flush(include_footers=True, chunk=chunk)
        self.request.finish()
        self._log()
        self._finished = True
        self.on_finish()
        self._break_cycles()

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
