import binascii
import hashlib
import hmac
from collections import OrderedDict

import bcrypt

from utils.text import force_bytes, force_text


def check_password(password, encoded):
    """
    Returns a boolean of whether the raw password matches the three
    part encoded digest.
    """
    return hasher.verify(password, encoded)


def make_password(password, salt=None):
    """
    Turn a plain-text password into a hash for database storage
    """
    if not salt:
        salt = hasher.salt()

    return hasher.encode(password, salt)


def mask_hash(hash, show=6, char="*"):
    """
    Returns the given hash, with only the first ``show`` number shown. The
    rest are masked with ``char`` for security reasons.
    """
    masked = hash[:show]
    masked += char * len(hash[show:])
    return masked


class BCryptSHA256PasswordHasher:
    """
    Secure password hashing using the bcrypt algorithm (recommended)

    This is considered by many to be the most secure algorithm but you
    must first install the bcrypt library.  Please be warned that
    this library depends on native C code and might cause portability
    issues.
    """
    algorithm = "bcrypt_sha256"
    digest = hashlib.sha256
    rounds = 12

    def salt(self):
        return bcrypt.gensalt(self.rounds)

    def encode(self, password, salt):
        # Hash the password prior to using bcrypt to prevent password
        # truncation as described in #20138.
        if self.digest is not None:
            # Use binascii.hexlify() because a hex encoded bytestring is
            # Unicode on Python 3.
            password = binascii.hexlify(self.digest(force_bytes(password)).digest())
        else:
            password = force_bytes(password)

        data = bcrypt.hashpw(password, salt)
        return "%s$%s" % (self.algorithm, force_text(data))

    def verify(self, password, encoded):
        algorithm, data = encoded.split('$', 1)
        assert algorithm == self.algorithm
        encoded_2 = self.encode(password, force_bytes(data))
        return hmac.compare_digest(force_bytes(encoded), force_bytes(encoded_2))

    def safe_summary(self, encoded):
        algorithm, empty, algostr, work_factor, data = encoded.split('$', 4)
        assert algorithm == self.algorithm
        salt, checksum = data[:22], data[22:]
        return OrderedDict([
            ('algorithm', algorithm),
            ('work factor', work_factor),
            ('salt', mask_hash(salt)),
            ('checksum', mask_hash(checksum)),
        ])

hasher = BCryptSHA256PasswordHasher()
