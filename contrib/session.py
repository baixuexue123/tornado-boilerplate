import pickle
import secrets


class InvalidSesssionID(Exception):
    """invalid session id"""
    pass


class Session:

    cache_key_prefix = 'session-'
    session_id_name = 'token'
    expire_seconds = 60 * 60 * 2

    def __init__(self, settings, session_id=None):
        self.backend = settings['backend']
        self.expire_seconds = settings['expire_seconds']
        self.session_id_name = settings['session_id_name']
        if session_id is None:
            self._new_session_id()
        else:
            self._check_session_id(session_id)
            self._session_id = session_id
        self._session_cache = self.load()
        self.modified = False

    def _new_session_id(self):
        self._session_id = secrets.token_urlsafe()
        return self._session_id

    def _check_session_id(self, sid):
        if not self.backend.exists(self.cache_key_prefix + sid):
            raise InvalidSesssionID("invalid session id")

    @property
    def cache_key(self):
        return self.cache_key_prefix + self._session_id

    @property
    def _session(self):
        return self._session_cache

    @property
    def id(self):
        return self._session_id

    def load(self):
        session_data = self.backend.get(self.cache_key)
        if session_data is not None:
            return pickle.loads(session_data)
        return {}

    def save(self):
        if self.modified and self._session_id:
            session_data = pickle.dumps(self._session)
            self.backend.set(self.cache_key, session_data, self.expire_seconds)
        elif self._session_cache:
            self.set_expiry()

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
        self.clear()
        self.delete()
        self._session_id = None

    def set_expiry(self, value=expire_seconds):
        self.backend.expire(self.cache_key, value)
