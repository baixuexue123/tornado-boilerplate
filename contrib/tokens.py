
try:
    import secrets
    def get_token():
        return secrets.token_urlsafe(32)
except ImportError:
    from uuid import uuid4
    def get_token():
        return str(uuid4())
