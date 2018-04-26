

class Query:
    def __init__(self, table, limit=None, offset=None,
                 order_by=None, distinct_on=None):
        self._select = []
        self._where = []
        self._from = table
        self._join = []
        self._params = []
        self._order_by = order_by
        self._limit = limit
        self._offset = offset
        self._distinct_on = distinct_on

    def select(self, column):
        if isinstance(column, (list, tuple)):
            self._select.extend(column)
        else:
            self._select.append(column)

    def where(self, sql, **kwargs):
        for k, v in kwargs.items():
            if isinstance(v, (list, tuple)):
                sql = sql.replace(':' + k, '(%s)' % ', '.join(['%s' for _ in v]))
                self._params.extend(v)
            else:
                sql = sql.replace(':' + k, '%s')
                self._params.append(v)
        self._where.append('(%s)' % sql)

    def join(self, clause):
        if clause not in self._join:
            self._join.append(clause)

    def count(self, column='*', _as=None):
        distinct = 'DISTINCT ' if self._distinct_on else ''
        if _as:
            select = f'COUNT({distinct}{column}) AS {_as}'
        else:
            select = f'COUNT({distinct}{column})'
        if self._where:
            join = ' '.join(self._join)
            where = ' AND '.join(self._where)
            sql = f'SELECT {select} FROM {self._from} {join} WHERE {where}'
        else:
            i = self._from.find(' ')
            if i == -1:
                sql = f'SELECT {select} FROM {self._from}'
            else:
                sql = 'SELECT %s FROM %s' % (select, self._from[0:i])
        return sql, self._params

    def order_by(self, columns):
        self._order_by = columns

    def limit(self, val):
        self._limit = val

    def offset(self, val):
        self._offset = val

    @property
    def sql(self):
        return str(self)

    @property
    def params(self):
        return self._params

    def __str__(self):
        select = ', '.join(self._select)
        join = ' '.join(self._join)
        distinct = 'DISTINCT' if self._distinct_on else ''
        where = ' AND '.join(self._where)
        sql = f'SELECT {distinct} {select} FROM {self._from} {join}'
        if where:
            sql += f' WHERE {where}'
        if self._order_by is not None:
            _ob = ', '.join(self._order_by)
            sql += ' ORDER BY %s' % _ob
        if self._limit is not None:
            sql += ' LIMIT %s' % self._limit
        if self._offset is not None:
            sql += ' OFFSET %s' % self._offset
        return sql

    def __iter__(self):
        yield str(self)
        yield self._params
