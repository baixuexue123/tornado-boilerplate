import binascii
import hashlib
import hmac
import random
import time

from settings import SECRET_KEY
from utils.text import force_bytes

try:
    random = random.SystemRandom()
    using_sysrandom = True
except NotImplementedError:
    import warnings
    warnings.warn('A secure pseudo-random number generator is not available '
                  'on your system. Falling back to Mersenne Twister.')
    using_sysrandom = False


def salted_hmac(key_salt, value, secret=None):
    """
    Returns the HMAC-SHA1 of 'value', using a key generated from key_salt and a
    secret (which defaults to settings.SECRET_KEY).

    A different key_salt should be passed in for every application of HMAC.
    """
    if secret is None:
        secret = SECRET_KEY

    key_salt = force_bytes(key_salt)
    secret = force_bytes(secret)

    # We need to generate a derived key from our base key.  We can do this by
    # passing the key_salt and our base key through a pseudo-random function and
    # SHA1 works nicely.
    key = hashlib.sha1(key_salt + secret).digest()

    # If len(key_salt + secret) > sha_constructor().block_size, the above
    # line is redundant and could be replaced by key = key_salt + secret, since
    # the hmac module does the same thing for keys longer than the block size.
    # However, we need to ensure that we *always* do this.
    return hmac.new(key, msg=force_bytes(value), digestmod=hashlib.sha1)


def get_random_string(length=12,
                      allowed_chars='abcdefghijklmnopqrstuvwxyz'
                                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
    """
    Returns a securely generated random string.

    The default length of 12 with the a-z, A-Z, 0-9 character set returns
    a 71-bit value. log_2((26+26+10)^12) =~ 71 bits
    """
    if not using_sysrandom:
        # This is ugly, and a hack, but it makes things better than
        # the alternative of predictability. This re-seeds the PRNG
        # using a value that is hard for an attacker to predict, every
        # time a random string is required. This may change the
        # properties of the chosen random sequence slightly, but this
        # is better than absolute predictability.
        random.seed(
            hashlib.sha256(
                ("%s%s%s" % (
                    random.getstate(),
                    time.time(),
                    SECRET_KEY)).encode('utf-8')
            ).digest())
    return ''.join(random.choice(allowed_chars) for _ in range(length))


def constant_time_compare(val1, val2):
    return hmac.compare_digest(force_bytes(val1), force_bytes(val2))


def _bin_to_long(x):
    """
    Convert a binary string into a long integer

    This is a clever optimization for fast xor vector math
    """
    return int(binascii.hexlify(x), 16)


def _long_to_bin(x, hex_format_string):
    """
    Convert a long integer into a binary string.
    hex_format_string is like "%020x" for padding 10 characters.
    """
    return binascii.unhexlify((hex_format_string % x).encode('ascii'))


def pbkdf2(password, salt, iterations, dklen=0, digest=None):
    """
    Implements PBKDF2 with the same API as Django's existing
    implementation, using the stdlib.

    This is used in Python 2.7.8+ and 3.4+.
    """
    if digest is None:
        digest = hashlib.sha256
    if not dklen:
        dklen = None
    password = force_bytes(password)
    salt = force_bytes(salt)
    return hashlib.pbkdf2_hmac(
        digest().name, password, salt, iterations, dklen)

