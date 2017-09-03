import time
import logging
import traceback
import concurrent.futures

import tornado.web
import tornado.escape
from tornado import httputil
from tornado.escape import json_decode
from tornado.concurrent import Future
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from contrib import torndb
from contrib.session import Session

logger = logging.getLogger('boilerplate.' + __name__)

executor = concurrent.futures.ThreadPoolExecutor(2)


class BaseHandler(tornado.web.RequestHandler):
    """A class to collect common handler methods - all other handlers should
    subclass this one.
    """

    def initialize(self):
        database = self.settings['database']
        self.db = torndb.Connection(
            host=database['host'], database=database['db'],
            user=database['use'], password=database['password']
        )

    @property
    def session(self):
        """ Returns a Session instance """
        if not hasattr(self, '__session_manager'):
            setattr(self, '__session_manager', Session(self))
        return getattr(self, '__session_manager')

    def on_finish(self):
        self.db.close()
        if hasattr(self, '__session_manager'):
            self.session.save()


class ApiHandler(BaseHandler):

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

    def success(self, **kwargs):
        if self._finished:
            raise RuntimeError("Cannot write() after finish()")

        self._write_buffer['token'] = self.session.id
        self._write_buffer['status'] = 1
        self._write_buffer.update(kwargs)

    def fail(self, fail_reason='', **kwargs):
        if self._finished:
            raise RuntimeError("Cannot write() after finish()")

        self._write_buffer['token'] = self.session.id
        self._write_buffer['status'] = 0
        self._write_buffer['fail_reason'] = fail_reason
        self._write_buffer.update(kwargs)

    def flush(self, include_footers=False, callback=None,  chunk=None):
        """Flushes the current output buffer to the network.

        The ``callback`` argument, if given, can be used for flow control:
        it will be run when all flushed data has been written to the socket.
        Note that only one flush callback can be outstanding at a time;
        if another flush occurs before the previous flush's callback
        has been run, the previous callback will be discarded.
        """
        if chunk is None:
            chunk = tornado.escape.json_encode(self._write_buffer)
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
                chunk = tornado.escape.json_encode(self._write_buffer)
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
        if "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            lines = [line for line in traceback.format_exception(*kwargs["exc_info"])]
            logger.error(''.join(lines))
        self.fail(fail_reason=self._reason)

    def load_json(self):
        """Load JSON from the request body and store them in
        self.request.arguments, like Tornado does by default for POSTed form
        parameters.

        If JSON cannot be decoded, raises an HTTPError with status 400.
        """
        try:
            self.request.arguments = json_decode(self.request.body)
        except ValueError:
            msg = "Could not decode JSON: %s" % self.request.body
            logger.debug(msg)
            raise tornado.web.HTTPError(400, msg)

    def get_json_argument(self, name, default=None):
        """Find and return the argument with key 'name' from JSON request data.
        Similar to Tornado's get_argument() method.
        """
        if default is None:
            default = self._ARG_DEFAULT
        if not self.request.arguments:
            self.load_json()
        if name not in self.request.arguments:
            if default is self._ARG_DEFAULT:
                msg = "Missing argument '%s'" % name
                logger.debug(msg)
                raise tornado.web.HTTPError(400, msg)
            logger.debug("Returning default argument %s, as we couldn't find "
                         "'%s' in %s" % (default, name, self.request.arguments))
            return default
        arg = self.request.arguments[name]
        logger.debug("Found '%s': %s in JSON arguments" % (name, arg))
        return arg


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
