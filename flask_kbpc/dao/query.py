import sqlalchemy

from sqlalchemy import exc
from sqlalchemy.orm import load_only

from flask_kbpc.dao.data import DataBuffer


class QueryBuffer:

    def __init__(self, query, model, view_flagged=False):
        self.query = query
        self.model = model
        self._ordered = False
        self.fields = []
        self.filters = None
        self.exclusions = []
        self.view_flagged = view_flagged
        self.prepare_filters()

    def exclude(self, fields):
        fields = self.model.fields(exc=fields)
        self.query = self.query.options(load_only(*fields))
        self.fields = fields
        return self

    def select(self, fields):
        self.fields = self.model.fields(inc=fields)
        self.query = self.query.options(load_only(*fields))
        return self

    def limit(self, count):
        if not isinstance(count, int) or count < 0:
            raise ValueError('Cannot process a non-integer for limit size')
        self.query = self.query.limit(count)
        return self

    def like(self, field, expression):
        self.query = self.query.filter(field.like(expression))
        return self

    def gtdate(self, field, date):
        field = self.model.normalise(field)
        self.query = self.query.filter(getattr(self.model, field) >= date)
        return self

    def ltdate(self, field, date):
        field = self.model.normalise(field)
        self.query = self.query.filter(getattr(self.model, field) <= date)
        return self

    def filter(self, filters):
        if not filters:
            filters = {}
        self.filters = self.model.checkfilters(filters)
        self.prepare_filters()
        return self

    def order_by(self, field=None, descending=False):
        order = self.model.id
        if field:
            order = field
            self._ordered = True
        if descending:
            order.desc()
        self.query = self.query.order_by(order)
        return self

    def filter_schema(self, schema, fields):
        return list(filter(lambda item: item.get('key') in fields, schema))

    def marshall(self, query, schema, fields):
        if not fields:
            fields = self.model.fields()
        return DataBuffer(query, self.filter_schema(schema, fields), self.exclusions)

    def exec(self, query):
        try:
            return query()
        except Exception as e:
            pass
            # db.session.rollback()
        except sqlalchemy.orm.exc.NoResultFound as e:
            return False

    def show_soft_deletes(self):
        self.view_flagged = True
        return self

    def prepare_filters(self):
        if not self.filters:
            filters = {}
            filters.update(active='Y')
            self.filters = filters
        if self.view_flagged:
            if self.filters.get('active', None):
                del self.filters['active']
        self.query = self.query.filter_by(**self.filters)

    def all(self):
        resp = self.exec(self.query.all)
        return self.marshall(resp, self.model.get_schema(), self.fields)

    def one(self):
        resp = self.exec(self.query.one)
        return self.marshall(resp, self.model.get_schema(), self.fields)

    def first(self):
        resp = self.exec(self.query.first)
        return self.marshall(resp, self.model.get_schema(), self.fields)

    def __iter__(self):
        return self.all()