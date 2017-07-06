import pickle
from uuid import uuid4


class Session:

    cache_key_prefix = 'session-'
    session_id_name = '_sessionid'
    expire_seconds = 60 * 60 * 2

    def __init__(self, handler):
        """
        Expects a tornado.web.RequestHandler
        """

        self.handler = handler
        self.settings = handler.settings
        self.secret_key = handler.settings['cookie_secret']
        session_settings = handler.settings['session']
        self.backend = session_settings['backend']
        self.expire_seconds = session_settings['expire_seconds']
        self.session_id_name = session_settings['session_id_name']

        self._session_id = self.handler.get_cookie(self.session_id_name)
        self._session_cache = self.load()
        self.modified = False

    @property
    def cache_key(self):
        return self.cache_key_prefix + self._get_or_create_session_id()

    @property
    def _session(self):
        return self._session_cache

    def _get_or_create_session_id(self):
        if self._session_id is None:
            self._session_id = self._get_new_session_id()
        return self._session_id

    def _get_new_session_id(self):
        session_id = str(uuid4())
        self.handler.set_cookie(self.session_id_name, session_id,
                                **self._cookie_settings())
        return session_id

    def _cookie_settings(self):
        cookie_settings = self.settings.get('cookies', {})
        cookie_settings.setdefault('expires', None)
        cookie_settings.setdefault('expires_days', None)
        return cookie_settings

    def load(self):
        session_data = self.backend.get(self.cache_key)
        if session_data is not None:
            return pickle.loads(session_data)
        return {}

    def save(self):
        if self.modified:
            session_data = pickle.dumps(self._session)
            self.backend.set(self.cache_key, session_data, self.expire_seconds)

    def update(self, dict_):
        self._session.update(dict_)
        self.modified = True

    def __contains__(self, key):
        return key in self._session

    def __getitem__(self, key):
        return self._session[key]

    def __setitem__(self, key, value):
        self._session[key] = value
        self.modified = True

    def __delitem__(self, key):
        del self._session[key]
        self.modified = True

    def get(self, key, default=None):
        return self._session.get(key, default)

    def pop(self, key, default=None):
        return self._session.pop(key, default)

    def has_key(self, key):
        return key in self._session

    def keys(self):
        return self._session.keys()

    def values(self):
        return self._session.values()

    def items(self):
        return self._session.items()

    def iteritems(self):
        return self._session.iteritems()

    def clear(self):
        self._session_cache = {}
        self.modified = True

    def delete(self):
        self.backend.delete(self.cache_key)

    def flush(self):
        """
        Removes the current session data from the database and regenerates the key
        """
        self.clear()
        self.delete()
        self._session_id = None
        self.handler.clear_cookie(self.session_id_name)

    def set_expiry(self, value=expire_seconds):
        self.backend.expire(self.cache_key, value)
