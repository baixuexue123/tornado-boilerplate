import json

from contrib import torndb
from settings import settings
from settings import CACHE_BACKEND


class Store:

    def __init__(self, db=None):
        self._db = db

    @property
    def db(self):
        if self._db is not None:
            return self._db
        if not hasattr(self, '__db_conn'):
            _db = settings['database']
            conn = torndb.Connection(
                host=_db['host'], database=_db['db'],
                user=_db['user'], password=_db['password'],
                max_idle_time=150
            )
            setattr(self, '__db_conn', conn)
        return getattr(self, '__db_conn')

    def __del__(self):
        if hasattr(self, '__db_conn'):
            self.db.close()

CONFIG_TYPES = ('string', 'array', 'json')

PRODUCT_SUB_TYPES = ('海纳API', '整合API', '光道', '流量引擎', '身份识别', '授权爬取服务')


class Config(Store):

    cache = CACHE_BACKEND
    key_prefix = 'config::'

    @classmethod
    def remove_cache(cls, name):
        cls.cache.delete(cls.key_prefix + name)

    def _get_from_db(self, name):
        return self.db.get("SELECT `type`, `value` FROM `config` WHERE `name`=%s", name)

    def __getitem__(self, name):
        conf = self.cache.get(self.key_prefix + name)
        if conf is None:
            conf = self._get_from_db(name)
            if conf is None:
                raise KeyError('%s does not exists' % name)
            self.cache.set(self.key_prefix + name, json.dumps(conf))
        else:
            conf = json.loads(conf)

        value = conf['value']
        if conf['type'] == 'array':
            value = value.split(',')
        elif conf['type'] == 'json':
            value = json.loads(value)
        return value

    def __setitem__(self, name, value):
        type_ = 'string'
        if isinstance(value, dict):
            value = json.dumps(value)
            type_ = 'json'
        elif isinstance(value, (list, tuple)):
            value = ','.join(value)
            type_ = 'array'

        self.db.execute(
            """
            INSERT INTO config (`name`, `value`, type) VALUES (%s,%s,%s) 
            ON DUPLICATE KEY UPDATE `name`=%s;
            """, name, value, type_, name
        )
        conf = {
            'value': value,
            'type': type_,
        }
        self.cache.set(self.key_prefix + name, json.dumps(conf))
