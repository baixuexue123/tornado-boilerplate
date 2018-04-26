import os
import re
import uuid
import base64


class cached_property(object):
    """
    Decorator that converts a method with a single self argument into a
    property cached on the instance.
    """
    def __init__(self, func, name=None):
        self.func = func
        self.__doc__ = getattr(func, '__doc__')
        self.name = name or func.__name__

    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        res = instance.__dict__[self.name] = self.func(instance)
        return res


def gen_cookie_secret():
    return base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)


EMAIL_PATTERN = re.compile("^([.a-zA-Z0-9_-])+@([a-zA-Z0-9_-])+(\.[a-zA-Z0-9_-])+")


def email_validate(email):
    try:
        return EMAIL_PATTERN.match(email)
    except TypeError:
        return False


def join_media_url(burl, relurl):
    if relurl.startswith('/'):
        relurl = os.path.relpath(relurl, start='/')
    return os.path.join(burl, relurl)
