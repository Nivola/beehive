# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import logging
from time import time
from six import b, ensure_binary, ensure_text
from sqlalchemy import  exc
from sqlalchemy.ext.declarative import declarative_base
from beehive.common.data import operation, query, transaction, cache_query
from beecell.simple import truncate, id_gen
from beecell.db import ModelError, QueryError
from datetime import datetime
import hashlib
from uuid import uuid4
from re import match
from sqlalchemy.dialects import mysql
from sqlalchemy import *
from sqlalchemy.schema import DDLElement
from sqlalchemy.ext import compiler
from sqlalchemy.orm.session import Session
from sqlalchemy.orm.query import Query
from sqlalchemy.sql.expression import TextClause
from sqlalchemy import event
from typing import List, Type, Tuple, Any, Union, Dict, TypeVar

# type var for model Objects

ENTITY = TypeVar('ENTITY')

Base = declarative_base()

logger = logging.getLogger(__name__)


class CreateView(DDLElement):
    def __init__(self, name, selectable):
        self.name = name
        self.selectable = selectable


class DropView(DDLElement):
    def __init__(self, name):
        self.name = name


@compiler.compiles(CreateView)
def compile_create_view(element, compiler, **kw):
    return "CREATE OR REPLACE VIEW %s AS %s" % (element.name, compiler.sql_compiler.process(element.selectable))


@compiler.compiles(DropView)
def compile_drop_view(element, compiler, **kw):
    return "DROP VIEW IF EXISTS %s" % (element.name)


def view(name, metadata, selectable=None, sql=None):
    t = table(name)

    for c in selectable.c:
        c._make_proxy(t)

    event.listen(metadata, 'after_create', CreateView(name, selectable))
    # CreateView(name, selectable).execute_at('after-create', metadata)

    event.listen(metadata, 'before_drop', DropView(name))
    # DropView(name).execute_at('before-drop', metadata)
    return t


class AuditData(object):
    """Basic orm audit entity

    :param creation_date: creation date
    """
    def __init__(self, creation_date=None):
        if creation_date is not None:
            self.creation_date = creation_date
        else:
            self.creation_date = datetime.today()

        self.modification_date = self.creation_date
        self.expiry_date = None

    creation_date = Column(DateTime())
    modification_date = Column(DateTime())
    expiry_date = Column(DateTime())


class BaseEntity(AuditData):
    """Basic orm entity

    :param id: database id
    :param uuid: unique id
    :param objid: authorization id
    :param desc: description
    :param active: active [true or false]
    """
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True)
    objid = Column(String(400))
    name = Column(String(100), unique=True)
    desc = Column(String(255))
    active = Column(Boolean())

    def __init__(self, objid, name, desc='', active=True):
        self.uuid = str(uuid4())
        self.objid = str(objid)
        self.name = name
        self.desc = desc
        self.active = active

        AuditData.__init__(self)

    @staticmethod
    def get_base_entity_sqlfilters(*args, **kvargs):
        """Get base sql filters

        :param id: filter by id
        :param uuid: filter by uuid
        :param objid: filter by objid
        :param name: filter by name
        :param desc: filter by desc
        :param active: filter by active
        :param filter_expired: if True read item with expiry_date <= filter_expiry_date
        :param filter_expiry_date: expire date
        :param filter_creation_date_start: creation date start
        :param filter_creation_date_stop: creation date stop
        :param filter_modification_date_start: modification date start
        :param filter_modification_date_stop: modification date stop
        :param filter_expiry_date_start: expiry date start
        :param filter_expiry_date_stop: expiry date stop
        :return: base filters
        """
        filters = []

        # id is unique
        filters.append(PaginatedQueryGenerator.get_sqlfilter_by_field('id', kvargs))
        filters.append(PaginatedQueryGenerator.get_sqlfilter_by_field('uuid', kvargs))
        filters.append(PaginatedQueryGenerator.get_sqlfilter_by_field('objid', kvargs))
        # filters.append(PaginatedQueryGenerator.get_sqlfilter_by_field('name', kvargs))
        filters.append(PaginatedQueryGenerator.get_sqlfilter_by_field('desc', kvargs))
        filters.append(PaginatedQueryGenerator.get_sqlfilter_by_field('active', kvargs))

        # expired
        if 'filter_expired' in kvargs and kvargs.get('filter_expired') is not None:
            if kvargs.get('filter_expired') is True:
                filters.append(' AND t3.expiry_date<=:filter_expiry_date')
            else:
                filters.append(' AND (t3.expiry_date>:filter_expiry_date OR t3.expiry_date is null)')

        # creation_date
        currField = 'filter_creation_date_start'
        if currField in kvargs and kvargs.get(currField) is not None:
            filters.append(' AND t3.creation_date>=:{field}'.format(field=currField))

        currField = 'filter_creation_date_stop'
        if currField in kvargs and kvargs.get(currField) is not None:
            filters.append(' AND t3.creation_date<=:{field}'.format(field=currField))

        # modification_date
        currField = 'filter_modification_date_start'
        if currField in kvargs and kvargs.get(currField) is not None:
            filters.append(' AND t3.modification_date>=:{field}'.format(field=currField))

        currField = 'filter_modification_date_stop'
        if currField in kvargs and kvargs.get(currField) is not None:
            filters.append(' AND t3.modification_date<=:{field}'.format(field=currField))

        # expiry_date
        currField = 'filter_expiry_date_start'
        if currField in kvargs and kvargs.get(currField) is not None:
            filters.append(' AND (t3.expiry_date is null OR t3.expiry_date>=:{field})'.format(field=currField))

        currField = 'filter_expiry_date_stop'
        if currField in kvargs and kvargs.get(currField) is not None:
            filters.append(' AND (t3.expiry_date is null OR t3.expiry_date<=:{field})'.format(field=currField))

        return filters

    def is_active(self):
        res = (self.active is True or self.active == 1) and self.expiry_date is None
        return res

    def disable(self):
        self.expiry_date = datetime.today()
        self.name += '%s-DELETED' % id_gen()
        self.active = False

    def __repr__(self):
        return '<%s id=%s, uuid=%s, obid=%s, name=%s, active=%s>' % (
            self.__class__.__name__, self.id, self.uuid, self.objid, self.name, self.active)


class PermTag(Base):
    """Permission tag

    :param value: tag value
    :param explain: tag explain
    """
    __tablename__ = 'perm_tag'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    value = Column(String(100), unique=True)
    explain = Column(String(400))
    creation_date = Column(DateTime())

    def __init__(self, value, explain=None):
        self.creation_date = datetime.today()
        self.value = value
        self.explain = explain

    def __repr__(self):
        return '<PermTag(%s, %s)>' % (self.value, self.explain)


class PermTagEntity(Base):
    """Permission tag entity association

    :param tag: tag id
    :param entity: entity id
    :param type: entity type
    """
    __tablename__ = 'perm_tag_entity'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    tag = Column(Integer)
    entity = Column(Integer)
    type = Column(String(200))

    __table_args__ = (
        Index('idx_tag_entity', 'tag', 'entity', unique=True),
    )

    def __init__(self, tag, entity, type):
        self.tag = tag
        self.entity = entity
        self.type = type

    def __repr__(self):
        return '<PermTagEntity(%s, %s, %s, %s)>' % (self.id, self.tag, self.entity, self.type)


class SchedulerState(object):
    PENDING = 'PENDING'
    STARTED = 'STARTED'
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'
    RETRY = 'RETRY'
    REVOKED = 'REVOKED'


class SchedulerTask(Base):
    """Scheduler task

    :param task_id: task id
    :param name: task name
    :param status: task status
    :param start_time: task start time
    """
    __tablename__ = 'scheduler_task'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True, index=True)
    objtype = Column(String(100), index=True)
    objdef = Column(String(200), index=True)
    objid = Column(String(400), index=True)
    name = Column(String(100))
    parent = Column(String(100))
    worker = Column(String(100))
    args = Column(Text())
    kwargs = Column(String(400))
    status = Column(String(20), index=True)
    result = Column(String(400))
    api_id = Column(String(45))
    start_time = Column(mysql.DATETIME(fsp=6), index=True)
    run_time = Column(mysql.DATETIME(fsp=6))
    stop_time = Column(mysql.DATETIME(fsp=6))
    counter = Column(Integer)

    def __init__(self, task_id, name, status, start_time):
        self.uuid = str(task_id)
        self.objtype = None
        self.objdef = None
        self.objid = None
        self.name = name
        self.parent = None
        self.worker = None
        self.args = None
        self.kwargs = None
        self.status = status
        self.result = None
        self.start_time = start_time
        self.run_time = start_time
        self.stop_time = None
        self.counter = 0

    def __repr__(self):
        return '<SchedulerTask(%s, %s, %s)>' % (self.id, self.uuid, self.name)


class SchedulerStep(Base):
    """Scheduler task step

    :param task_id: task id
    :param name: step name
    """
    __tablename__ = 'scheduler_step'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True, index=True)
    name = Column(String(100))
    task_id = Column(String(50), index=True)
    status = Column(String(20))
    result = Column(String(400))
    start_time = Column(mysql.DATETIME(fsp=6))
    run_time = Column(mysql.DATETIME(fsp=6))
    stop_time = Column(mysql.DATETIME(fsp=6))

    def __init__(self, task_id, name):
        self.uuid = str(uuid4())
        self.name = name
        self.task_id = task_id
        self.status = SchedulerState.STARTED
        self.result = None
        self.start_time = datetime.today()
        self.run_time = self.start_time
        self.stop_time = None

    def __repr__(self):
        return '<SchedulerStep(%s, %s, %s)>' % (self.id, self.uuid, self.name)


class SchedulerTrace(Base):
    """Scheduler task trace

    :param task_id: task id
    :param step_id: step id
    :param message: task message
    :param level: task message level
    """
    __tablename__ = 'scheduler_trace'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    task_id = Column(String(50), index=True)
    step_id = Column(String(50), index=True)
    message = Column(Text())
    level = Column(String(10), index=True)
    date = Column(mysql.DATETIME(fsp=6))

    def __init__(self, task_id, step_id, message, level):
        self.task_id = task_id
        self.step_id = step_id
        self.message = message
        self.level = level
        self.date = datetime.today()

    def __repr__(self):
        return '<SchedulerTrace(%s, %s, %s)>' % (self.task_id, self.step_id, self.level)


class PaginatedQueryGenerator(object):
    """Use this class to generate and configure query with pagination and filtering based on tagged entity.
    Base table : perm_tag t1, perm_tag_entity t2, {entitytable} t3

    :param entity: main mapper entity
    :param session: sqlalchemy session
    :param other_entities: other mapper entities [default=[]]
    :param custom_select: custom select used instead of entity table [optional]
    :param with_perm_tag: check permission tags [optional]
    """
    def __init__(self, entity: Type[ENTITY], session: Session, other_entities=[], custom_select: str=None,
                 with_perm_tag: bool=True):
        self.logger = logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)

        self.session: Session = session
        self.entity = entity
        self.custom_select: str = custom_select
        self.other_entities = other_entities
        self.other_tables: List[str] = []
        self.other_filters: List[str] = []
        self.filter_fields: List[str] = []
        self.select_fields: List[str] = ['t3.*']
        self.with_perm_tag: bool = with_perm_tag
        self.joins = []
        self.group_by: bool = False
        self.page: int = None
        self.size: int = None
        self.order: str = None
        self.field: str = None
        self.start: str = None
        self.end: str = None

    def set_pagination(self, page=0, size=10, order='DESC', field='id'):
        """Set pagiantion params

        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        """
        if field == 'id':
            field = 't3.id'

        self.page: int = page
        self.size: int = size
        self.order: str = order
        self.field: str = field
        self.start: str = str(size * page)
        self.end: str = str(size * (page + 1))

    def add_table(self, table: str, alias: str):
        """Append table to query

        :param str table: table name
        :param str alias: table alias
        """
        self.other_tables.append([table, alias])

    def add_join(self, table: str, alias: str, on: str, left: bool=False, inner: bool=False, outer: bool=False):
        """Append join to query

        :param str table: table name
        :param str alias: table alias
        :param str on: join on clause
        :param bool left: if True create a left join
        :param bool inner: if True create an inner join
        :param bool outer: if True create an outer join
        """
        join = 'join %s %s on %s' % (table, alias, on)
        if inner is True:
            join = 'inner ' + join
        elif outer is True:
            join = 'outer ' + join
        if left is True:
            join = 'left ' + join
        self.joins.append(join)

    def add_select_field(self, field: str):
        """Append field to add after SELECT

        :param str field: field with syntax <table_ alias>.<field>
        """
        self.select_fields.append(field)

    def add_filter_by_field(self, field, kvargs, custom_filter=None):
        """Add where condition like AND t3.<field>=:<field> if <field> in kvargs and not None. If you want a different
        filter syntax use custom_filter.

        :param field: field to search in kvargs
        :param kvargs: query custom params
        :param custom_filter: custom string filter [optional]
        """
        if field in kvargs and kvargs.get(field) is not None:
            if custom_filter is None:
                self.other_filters.append('AND t3.{field}=:{field}'.format(field=field))
            else:
                self.other_filters.append(custom_filter)

    @staticmethod
    def get_sqlfilter_by_field(field, kvargs, op=' AND'):
        """Add where condition like 'AND t3.<field>=:<field>' if <field> in kvargs and not None..

        :param field: field to search in kvargs
        :param kvargs: query custom params
        :param op: operation [default=' AND']
        """
        if kvargs.get(field, None) is not None:
            return PaginatedQueryGenerator.create_sqlfilter(field, op_logical=op)
        else:
            return ''

    @staticmethod
    def get_like_sqlfilter_by_field(field, column, kvargs, op=' AND'):
        """Add where condition like 'AND t3.<field> like :<field>' if <field> in kvargs and not None..

        :param field: field to search in kvargs
        :param column: name of the column in table
        :param kvargs: query custom params
        :param op: operation [default=' AND']
        """
        # if field in kvargs and kvargs.get(field) is not None:
        if kvargs.get(field, None) is not None:
            return PaginatedQueryGenerator.create_sqlfilter(field, column=column, op_logical=op, op_comparison=' like ')
        else:
            return ''

    @staticmethod
    def create_sqlfilter(param:str, column:str=None, op_logical:str=' AND', op_comparison:str='=', alias:str='t3')->str:
        """create sql where condition filter like 'AND t3.<field>=:<field>' if <field> in kvargs and not None..

        :param param: query custom params
        :param column: name of the column in table [optional]
        :param op_logical: operation [default=' AND']
        :param op_comparison: comparison [default='=']
        :param alias: table alias [default='t3']
        """
        if column is None:
            column = param

        if column is not None:
            res = ' {op_logical} {alias}.{column}{op_comparison}:{param}'.format(
                column=column, param=param, op_logical=op_logical, op_comparison=op_comparison, alias=alias)
            return res
        else:
            return ''

    def add_filter(self, sqlfilter:str):
        """Append filter to query

        :param str sqlfilter: sql filter like 'AND t3.id=101'
        """
        self.other_filters.append(sqlfilter)

    def add_relative_filter(self, sqlfilter:str, field_name:str, kvargs) :
        """Append filter to query

        :param str sqlfilter: sql filter like 'AND t3.id=101'
        :param field_name: name of the field used in filter
        :param kvargs: args to parse that contains field
        """
        if field_name in kvargs and kvargs.get(field_name) is not None:
            self.other_filters.append(sqlfilter)

    def base_stmp(self, count: bool=False)-> TextClause:
        """Base statement

        :param count: if True return statement for count
        """
        fields = ', '.join(self.select_fields)
        if count is True:
            fields = 'count(distinct {field}) as count'.format(field=self.field)

        sql = ['SELECT {fields}', 'FROM {table} t3']
        if self.with_perm_tag is True:
            sql.extend([
                ', perm_tag t1, perm_tag_entity t2 '
            ])

        # append other tables
        for table in self.other_tables:
            sql.append(', %s %s' % (table[0], table[1]))

        sql.extend([
            'WHERE 1=1'
        ])
        # set base where
        if self.with_perm_tag is True:
            sql.extend([
                'AND t3.id=t2.entity AND t2.tag=t1.id',
                'AND t1.value IN :tags '
            ])

        # add filters
        for sqlfilter in self.other_filters:
            sql.append(sqlfilter)

            # set group by and limit
        if count is False:
            if not hasattr(self.entity, '__view__') and self.with_perm_tag is True:
                sql.extend([
                    'GROUP BY {field}',
                    'ORDER BY {field} {order}'
                ])
            elif self.group_by is True:
                sql.extend([
                    'GROUP BY {field}',
                    'ORDER BY {field} {order}'
                ])
            else:
                sql.extend([
                    'ORDER BY {field} {order}'
                ])
            if self.size > 0:
                sql.append('LIMIT {start},{size}')
            elif self.size == -1:
                sql.append('')
            else:
                sql.append('LIMIT 1000')  # num rows

        # format query
        stmp: str = ' '.join(sql)
        # custom table like select
        if self.custom_select is not None:
            table = self.custom_select
        # table is defined by entity
        else:
            table = '`%s`' % self.entity.__tablename__
        stmp = stmp.format(table=table, fields=fields, field=self.field, order=self.order, start=self.start,
                           size=self.size)
        # self.logger.debug2('query: %s' % stmp)
        res: TextClause = text(stmp)
        return res

    def run(self, tags, *args, **kvargs):
        """Make query

        :param list tags: list of permission tags
        :param args: custom args
        :param kvargs: custom kvargs
        """
        start = time()

        self.group_by = kvargs.pop('group_by', False)

        if self.with_perm_tag is True:
            self.logger.debug2('Authorization with permission tags ENABLED')
        else:
            self.logger.debug2('Authorization with permission tags DISABLED')

        if tags is None or len(tags) == 0:
            tags = ['']

        # make query
        if self.size > 0:
            # count all records
            stmp = self.base_stmp(count=True)
            total = self.session.query(Column('count')).from_statement(stmp).params(tags=tags, **kvargs).first()[0]

        stmp = self.base_stmp()

        # set query entities
        entities = [self.entity]
        entities.extend(self.other_entities)

        query = self.session.query(*entities).from_statement(stmp).params(tags=tags, **kvargs)
        self.logger.debug2('stmp: %s' % query.statement.compile(dialect=mysql.dialect()))
        self.logger.debug2('kvargs: %s' % truncate(kvargs, size=2000))
        self.logger.debug2('tags: %s' % truncate(tags))
        res = query.all()

        if self.size == 0 or self.size == -1:
            total = len(res)

        elapsed = round(time() - start, 3)
        self.logger.debug2('Get %ss (total:%s): %s [%s]' % (self.entity.__tablename__, total, truncate(res), elapsed))
        return res, total

    def base_stmp2(self, count: bool = False, limit: int=1000) -> TextClause:
        """Base statement. Change usage respect base_smtp. Use distinct in select and remove group by

        :param count: if True return statement for count
        :param limit: max returned records [default=1000]
        """
        fields = ', '.join(self.select_fields)
        if count is True:
            fields = 'count(distinct {field}) as count'.format(field=self.field)

        sql = ['SELECT distinct {fields}', 'FROM {table} t3']
        if self.with_perm_tag is True:
            sql.extend([
                'inner join perm_tag_entity t2 on  t3.id=t2.entity',
                'inner join perm_tag t1 on t2.tag=t1.id'
            ])

        # append other tables
        for join in self.joins:
            sql.append(join)

        sql.extend([
            'WHERE 1=1'
        ])

        # set base where
        if self.with_perm_tag is True:
            sql.extend([
                'AND t1.value IN :tags '
            ])

        # add filters
        for sqlfilter in self.other_filters:
            sql.append(sqlfilter)

        # set group by and limit
        if count is False:
            sql.extend([
                'ORDER BY {field} {order}'
            ])

            if self.size > 0:
                sql.append('LIMIT {start},{size}')
            elif self.size == -1:
                sql.append('')
            else:
                sql.append('LIMIT %s' % limit)  # num rows

        # format query
        stmp = ' '.join(sql)

        # custom table like select
        if self.custom_select is not None:
            table = self.custom_select

        # table is defined by entity
        else:
            table = '`%s`' % self.entity.__tablename__
        stmp = stmp.format(table=table, fields=fields, field=self.field, order=self.order, start=self.start,
                           size=self.size)

        # self.logger.debug2('query: %s' % stmp)

        res: TextClause = text(stmp)
        return res

    def run2(self, tags: List[str], *args, **kvargs) -> Tuple[List[ENTITY], int]:
        """Make query. Use base_smtp2

        :param list tags: list of permission tags
        :param args: custom args
        :param kvargs: custom kvargs
        """
        start = time()

        if self.with_perm_tag is True:
            self.logger.debug2('Authorization with permission tags ENABLED')
        else:
            self.logger.debug2('Authorization with permission tags DISABLED')

        if tags is None or len(tags) == 0:
            tags = ['']

        # make query
        if self.size > 0:
            # count all records
            stmp = self.base_stmp2(count=True)
            total = self.session.query(Column('count')).from_statement(stmp).params(tags=tags, **kvargs).first()[0]

        stmp = self.base_stmp2()

        # set query entities
        entities = [self.entity]
        entities.extend(self.other_entities)

        query = self.session.query(*entities).from_statement(stmp).params(tags=tags, **kvargs)
        self.logger.debug2('stmp: %s' % query.statement.compile(dialect=mysql.dialect()))
        self.logger.debug2('kvargs: %s' % truncate(kvargs))
        self.logger.debug2('tags: %s' % truncate(tags))
        res: List[ENTITY] = query.all()

        if self.size == 0 or self.size == -1:
            total: int = len(res)

        elapsed = round(time() - start, 3)
        self.logger.debug2('Get %ss (total:%s): %s [%s]' % (self.entity.__tablename__, total, truncate(res), elapsed))
        return res, total


class AbstractDbManager(object):
    """Abstract db manager

    :param session: sqlalchemy session
    """
    def __init__(self, session=None, cache_manager=None, ttl=600):
        self.logger = logging.getLogger(self.__class__.__module__ +  '.' + self.__class__.__name__)

        self._session: Session = session
        self.cache_manager = cache_manager
        self.cache_ttl = ttl

    def __del__(self):
        pass

    def __repr__(self):
        return "<%s id='%s'>" % (self.__class__.__name__, id(self))

    def __str__(self):
        return "<%s id='%s'>" % (self.__class__.__name__, id(self))

    @property
    def cache(self):
        return self.cache_manager

    def get_session(self) -> Session:
        if self._session is None:
            return operation.session
        else:
            return self._session

    @staticmethod
    def create_table(db_uri):
        """Create all tables in the engine. This is equivalent to "Create Table" statements in raw SQL

        :param db_uri: db uri
        """
        try:
            engine = create_engine(db_uri)
            engine.execute('SET FOREIGN_KEY_CHECKS=1;')
            Base.metadata.create_all(engine)
            logger.info('Create tables on : %s' % db_uri)
            del engine
        except exc.DBAPIError as e:
            raise Exception(e)

    @staticmethod
    def remove_table(db_uri):
        """Remove all tables in the engine. This is equivalent to "Drop Table" statements in raw SQL

        :param db_uri: db uri
        """
        try:
            engine = create_engine(db_uri)
            engine.execute('SET FOREIGN_KEY_CHECKS=0;')
            Base.metadata.drop_all(engine)
            logger.info('Remove tables from : %s' % db_uri)
            del engine
        except exc.DBAPIError as e:
            raise Exception(e)

    def map_field_to_column(self, fields):
        return [Column(f) for f in fields]

    def print_stmp(self, stmp):
        """Print a query statement

        :param stmp: statement
        """
        self.logger.debug2('stmp: %s' % stmp.statement.compile(dialect=mysql.dialect()))

    @query
    def count_entities(self, entityclass: Type[ENTITY]) -> int:
        """Get model entity count.

        :return: entity count
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()
        res: int = session.query(entityclass).count()

        self.logger.debug2('Count %s: %s' % (entityclass.__name__, res))
        return res

    def print_query(self, func, query: Query, args):
        """Print query

        :param func: function that run the query
        :param query: query to run
        :param args: query args. Use: inspect.getargvalues(inspect.currentframe())
        """
        self.logger.debug2('stmp: %s' % query.statement.compile(dialect=mysql.dialect()))
        args = {arg: args.locals[arg] for arg in args.args}
        self.logger.debug2(args)

    def query_entities(self, entityclass: Type[ENTITY], session: Session, oid: Union[str, int] = None,
                       objid: str = None, uuid :str = None, name: str =None, *args, **kvargs) -> Query:
        """Get model entities query

        :param entityclass: entity model class
        :param session: db session
        :param int oid: entity id. [optional]
        :param str objid: entity authorization id. [optional]
        :param str uuid: entity uuid. [optional]
        :param str name: entity name. [optional]
        :param dict kvargs: additional filters [optional]
        :return: list of entityclass
        :raises ModelError: raise :class:`ModelError`
        """
        if oid is not None:
            query = session.query(entityclass).filter_by(id=oid)
        elif objid is not None:
            query = session.query(entityclass).filter_by(objid=objid)
        elif uuid is not None:
            query = session.query(entityclass).filter_by(uuid=uuid)
        elif name is not None:
            query = session.query(entityclass).filter_by(name=name)
        else:
            query = session.query(entityclass)

        query = query.filter_by(**kvargs)

        self.logger.debug2('stmp: %s' % query.statement.compile(dialect=mysql.dialect()))
        self.logger.debug2('kvargs: %s, %s, %s, %s, %s' % (kvargs, oid, objid, uuid, name))

        return query

    @query
    def exist_entity(self, entityclass: Type[ENTITY], oid: Union[str, int], *args, **kvargs) -> bool:
        """Parse oid and check entity exists

        :param entityclass: entity model class
        :param oid: entity model id or name or uuid
        :param dict kvargs: additional filters [optional]
        :return: True if exists
        """
        session = self.get_session()

        if oid is None:
            raise ModelError('%s %s not found' % (oid, entityclass.__name__))

        if isinstance(oid, int):
            oid = str(oid)

        # get obj by uuid
        if match('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', oid):
            search_field = 'uuid'
            entity = self.query_entities(entityclass, session, uuid=oid, *args, **kvargs)
        # get obj by id
        elif match('^\d+$', oid):
            search_field = 'id'
            entity = self.query_entities(entityclass, session, oid=oid, *args, **kvargs)
        # get obj by name
        elif match('[\-\w\d]+', oid):
            search_field = 'name'
            entity = self.query_entities(entityclass, session, name=oid, **kvargs)

        resp: bool = False
        if oid is not None:
            res = entity.one_or_none()
            if res is not None:
                resp = True

        self.logger.debug2('Check entity %s by %s %s exists: %s' % (entityclass.__name__, search_field, oid, resp))
        return resp

    @query
    def get_entity(self, entityclass: Type[ENTITY], oid: Union[str, int], for_update: bool=False, *args, **kvargs) \
            -> ENTITY:
        """Parse oid and get entity by name or by model id or by uuid

        :param entityclass: entity model class
        :param oid: entity model id or name or uuid
        :param dict kvargs: additional filters [optional]
        :param for_update: True if model is get for update [default=False]
        :return: list of entityclass
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()

        if oid is None:
            raise ModelError('%s %s not found' % (oid, entityclass.__name__))

        if isinstance(oid, int):
            oid = str(oid)

        # get obj by uuid
        if match('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', oid):
            search_field = 'uuid'
            entity = self.query_entities(entityclass, session, uuid=oid, *args, **kvargs)
        # get obj by id
        elif match('^\d+$', oid):
            search_field = 'id'
            entity = self.query_entities(entityclass, session, oid=oid, *args, **kvargs)
        # get obj by name
        elif match('[\-\w\d]+', oid):
            search_field = 'name'
            entity = self.query_entities(entityclass, session, name=oid, **kvargs)

        res: ENTITY = None
        if for_update:
            res = entity.with_for_update().first()
        else:
            res = entity.first()

        if res is None:
            msg = 'No %s found' % entityclass.__name__
            self.logger.error(msg)
            raise ModelError(msg, code=404)

        self.logger.debug2('Query entity %s by %s %s: %s' % (entityclass.__name__, search_field, oid, res))
        return res

    @cache_query('get')
    def get_entity_with_cache(self, entityclass: Type[ENTITY], oid: Union[str, int], *args, **kvargs) -> ENTITY:
        """Search entity in cache and return if exist otherwise exec query in database

        :param entityclass: entity model class
        :param oid: entity model id or name or uuid
        :param ttl: cache ttl [default=120]
        :param dict kvargs: additional filters [optional]
        :return: list of entityclass
        :raises QueryError: raise :class:`QueryError`
        """
        try:
            ret: ENTITY = self.get_entity(entityclass, oid, *args, **kvargs)
        except QueryError as ex:
            raise ModelError('Resource %s not found' % oid)
        if ret is None:
            raise ModelError('Resource %s not found' % oid)
        return ret

    @cache_query('list')
    def get_entities_with_cache(self, entityclass: Type[ENTITY], oid='', *args, **kvargs) -> List[ENTITY]:
        """Search entities in cache and return if exist otherwise exec query in database. Do not use permission tag.

        :param entityclass: entity model class
        :param oid: entity model id or name or uuid
        :return: list of entityclass
        :raises QueryError: raise :class:`QueryError`
        """
        res: List[ENTITY]
        res, tot = self.get_paginated_entities(entityclass, size=-1, with_perm_tag=False, *args, **kvargs)
        return res

    def add_base_entity_filters(self, query: Query, *args, **kvargs)-> Query:
        """Add base filter to sqlalchemy entity query

        :param args: positional args
        :param kvargs: key value args
        :param kvargs.id: database id [optional]
        :param kvargs.uuid: unique id [optional]
        :param kvargs.objid: authorization id [optional]
        :param kvargs.name: name [optional]
        :param kvargs.desc: description [optional]
        :param kvargs.active: active [optional]
        :return: query with filters
        """
        oid = kvargs.get('id', None)
        uuid = kvargs.get('uuid', None)
        objid = kvargs.get('objid', None)
        name = kvargs.get('name', None)
        desc = kvargs.get('desc', None)
        active = kvargs.get('active', None)

        # id is unique
        if oid is not None:
            query = query.filter_by(id=oid)

        # uuid is unique
        if uuid is not None:
            query = query.filter_by(uuid=uuid)

        # Non unique filters
        if objid is not None:
            query = query.filter_by(objid=objid)
        if name is not None:
            query = query.filter_by(name=name)
        if desc is not None:
            query = query.filter_by(desc=desc)
        if active is not None:
            query = query.filter_by(active=active)

        return query

    @query
    def get_paginated_entities(self, entityclass: Type[ENTITY],
                               tags: List[str]=[],
                               page=0,
                               size=10,
                               order: str ='DESC',
                               field: str ='t3.id',
                               filters: List[str]=[],
                               tables: List[Tuple[str, str]]=[],
                               joins: List[Tuple[str, str, str, bool, bool]]=[],
                               select_fields: List[str]=[],
                               custom_select: str=None,
                               with_perm_tag: bool=True,
                               *args, **kvargs) -> List[ENTITY]:
        """Get entities associated with some permission tags

        :param entityclass: entity class
        :param tags: list of permission tags
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=t3.id]
        :param filters: sql filters to apply [optional]
        :param tables: sql tables to add (table_name, alias) [optional]
        :param joins: sql tables to join  list of tuple definig  table name, alias, join condition, flag left join , flag inner join (table_name:str, alias:str, on:str, left: bool inner: bool )  [optional]
        :param select_fields: list of fields to add to select [optional]
        :param custom_select: custom select [optional]
        :param with_perm_tag: if False disable control of permission tags [default=True]
        :param args: custom params
        :param kvargs: custom params
        :param kvargs.name: name [optional]
        :param kvargs.desc: desc [optional]
        :param kvargs.names: name like [optional]
        :param kvargs.active: active [optional]
        :param kvargs.creation_date: creation_date [optional]
        :param kvargs.modification_date: modification_date [optional]
        :return: list of entityclass
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()

        query = PaginatedQueryGenerator(entityclass, session, with_perm_tag=with_perm_tag, custom_select=custom_select)
        # set tables
        for table, alias in tables:
            query.add_table(table, alias)

        for table, alias, on, left, inner in joins:
            query.add_join(table, alias, on, left=left, inner=inner, outer=(not inner))

        # add select fields
        for item in select_fields:
            query.add_select_field(item)

        # set filters
        query.add_filter_by_field('name', kvargs, custom_filter='AND t3.name like :name')
        query.add_filter_by_field('desc', kvargs, custom_filter='AND t3.desc like :desc')
        query.add_filter_by_field('active', kvargs)
        query.add_filter_by_field('creation_date', kvargs)
        query.add_filter_by_field('modification_date', kvargs)

        for item in filters:
            query.add_filter(item)
        query.set_pagination(page=page, size=size, order=order, field=field)
        res: List[ENTITY]
        if kvargs.pop('run2', False) is True:
            res = query.run2(tags, *args, **kvargs)
        else:
            res = query.run(tags, *args, **kvargs)
        return res

    @transaction
    def add_entity(self, entityclass, *args, **kvargs):
        """Add an entity.

        :param entityclass: entity model class
        :param args: positional args
        :param kvargs: key value args
        :return: new entity
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # create entity
        record = entityclass(*args, **kvargs)
        session.add(record)
        session.flush()

        self.logger.debug2('Add %s: %s' % (entityclass.__name__, truncate(record)))
        return record

    @transaction
    def update_entity(self, entityclass, *args, **kvargs)-> Union[str, int]:
        """Update entity.

        :param entityclass: entity model class
        :param args: positional args
        :param kvargs: date to update. [optional]
        :param kvargs.oid: database id [optional]
        :param kvargs.uuid: unique id [optional]
        :return: entity oid
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # get entity
        oid: Union[str, int] = kvargs.pop('oid', None)
        uuid = kvargs.pop('uuid', None)
        if oid is not None:
            query = self.query_entities(entityclass, session, oid=oid)
        elif uuid is not None:
            query = self.query_entities(entityclass, session, uuid=uuid)
            oid = uuid
        else:
            raise ModelError('Neither oid nor uuid are been specified', code=400)

        # check entity exists
        entity = query.first()
        if entity is None:
            msg = 'No %s found' % entityclass.__name__
            self.logger.error(msg)
            raise ModelError(msg, code=404)

        params = {}
        for k, v in kvargs.items():
            if v is not None:
                params[k] = v

        # create data dict with update
        if getattr(entityclass, 'modification_date', None) is not None:
            params['modification_date'] = datetime.today()

        query.update(params, synchronize_session=False)
        # session.flush()

        self.logger.debug2('Update %s %s with data: %s' % (entityclass.__name__, oid, params))
        return oid

    @transaction
    def update_entity_null(self, entityclass, **kvargs):
        """Update entity.

        :param entityclass: entity model class
        :param args: positional args
        :param kvargs: date to update. [optional]
        :param kvargs.oid: database id [optional]
        :param kvargs.uuid: unique id [optional]
        :return: entity oid
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # get entity
        oid = kvargs.pop('oid', None)
        uuid = kvargs.pop('uuid', None)
        if oid is not None:
            query = self.query_entities(entityclass, session, oid=oid)
        elif uuid is not None:
            query = self.query_entities(entityclass, session, uuid=uuid)
            oid = uuid
        else:
            raise ModelError('Neither oid nor uuid are been specified', code=400)

        # check entity exists
        entity = query.first()
        if entity is None:
            msg = 'No %s found' % entityclass.__name__
            self.logger.error(msg)
            raise ModelError(msg, code=404)

        # create data dict with update
        kvargs['modification_date'] = datetime.today()

        query.update(kvargs)
        session.flush()

        self.logger.debug2('Update null %s %s with data: %s' % (entityclass.__name__, oid, kvargs))
        return oid

    @transaction
    def remove_entity(self, entityclass, *args, **kvargs):
        """Remove entity.

        :param entityclass: entity model class
        :param args: positional args
        :param kvargs: date to update. [optional]
        :param kvargs.oid: database id [optional]
        :param kvargs.uuid: unique id [optional]
        :return: entity oid
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # get entity
        query = self.query_entities(entityclass, session, **kvargs)

        # check entity exists
        entity = query.first()
        if entity is None:
            msg = 'No %s found' % entityclass.__name__
            self.logger.error(msg)
            raise ModelError(msg, code=404)

        # delete entity
        session.delete(entity)

        self.logger.debug2('Remove %s %s' % (entityclass.__name__, entity.id))
        return entity.id

    @transaction
    def add(self, entity):
        """Add an entity using as input parameter the orm entity instance

        :param entity: orm entity instance
        :return: orm entity instance
        :raises TransactionError: raise :class:`TransactionError`
        """
        if entity is None:
            raise QueryError('Error: can\'t not add None entity')

        session = self.get_session()
        session.add(entity)
        session.flush()
        self.logger.debug2('Add %s entity %s' % (entity.__class__.__name__, entity))
        return entity

    @transaction
    def add_all(self, entities):
        """Add a list of entities using as input parameter the list of orm entity instances

        :param entities: list of orm entity instance
        :return: num of orm entity instance
        :raises TransactionError: raise :class:`TransactionError`
        """
        if entities is None:
            raise QueryError('Error: can\'t not add None entity')

        session = self.get_session()
        session.add_all(entities)
        session.flush()
        self.logger.debug2('Add all %s entity %s' % (entities[0].__class__.__name__, len(entities)))
        return len(entities)

    @transaction
    def update(self, entity):
        """Update an entity using as input parameter the orm entity instance

        :param entity: orm entity instance
        :return: orm entity instance
        :raises TransactionError: raise :class:`TransactionError`
        """
        if entity is None:
            raise QueryError('Error: can\'t not update None entity')

        self.logger.info('Update %s entity %s' % (entity.__class__.__name__, entity))
        if isinstance(entity, AuditData):
            entity.modification_date = datetime.now()

        session = self.get_session()
        session.merge(entity)
        session.flush()
        self.logger.info('Updated')
        return entity

    @transaction
    def bulk_save_entities(self, entities):
        """Perform a bulk save of the given list of entities

        :param entities: list of orm entity instance
        :return: list of orm entity instance
        :raises TransactionError: raise :class:`TransactionError`
        """
        if entities is None:
            raise QueryError('Error: can \'t not bulk update None entities')

        for entity in entities:
            self.logger.debug('Update %s entity %s' % (entities.__class__.__name__, entity))
            if isinstance(entity, BaseEntity):
                entity.modification_date = datetime.today()

        session = self.get_session()
        session.bulk_save_objects(entities)
        session.flush()
        self.logger.info('Bulk updated %s entities' % len(entities))
        return entities

    @transaction
    def delete(self, entity):
        """Delete entity

        :param entity: orm entity instance
        :return: orm entity instance
        :raises TransactionError: raise :class:`TransactionError`
        """
        if entity is None:
            raise QueryError('Error: can\'t not delete None entity')

        self.logger.debug2('Delete %s entity %s' % (entity.__class__.__name__, entity))
        if isinstance(entity, BaseEntity):
            if entity.is_active():
                entity.disable()
                self.update(entity)
                logger.info('Disable entity %s' % entity.id)
            else:
                logger.info('Nothing to do on %s !' % entity)
        else:
            self.purge(entity)
            logger.info('Purge entity %s' % entity.id)
        return entity

    @transaction
    def purge(self, entity):
        """Hard delete entity

        :param entity: entity
        :return Boolean:
        """
        if entity is None:
            logger.warning('Warning: can\'t not purge None entity')
            return entity

        session = self.get_session()
        session.delete(entity)
        session.flush()
        logger.debug2('Delete %s entity %s' % (entity.__class__.__name__, entity))

    #
    # permission tag
    #
    def get_all_valid_objids(self, args):
        """Get a list of authorization ids that map object

        :param args: objid split by //
        :return: list of valid objids
        """
        # first item *.*.*.....
        act_obj = ['*' for i in args]
        objdis = ['//'.join(act_obj)]
        if args[0] != '*':
            pos = 0
            for arg in args:
                act_obj[pos] = arg
                objdis.append('//'.join(act_obj))
                pos += 1

        return objdis

    def hash_from_permission(self, objdef, objid):
        """Get hash from entity permission (objdef, objid)

        :param objdef: enitity permission object type definition
        :param objid: enitity permission object id
        """
        perm = b('%s-%s' % (objdef.lower(), objid))
        tag = hashlib.md5(perm).hexdigest()
        return tag

    @query
    def get_perm_tag(self, value=None, explain=None, *args, **kvargs):
        """Get permission tag

        :param value: tag value [optional]
        :param explain: tag explain [optional]
        :return: list of permtag
        :raises QueryError: raise :class:`QueryError`
        """
        session = self.get_session()

        query = session.query(PermTag)

        if value is not None:
            query = query.filter_by(value=value)
        elif explain is not None:
            query = query.filter(PermTag.explain.like('%'+explain+'%'))

        res = query.all()

        self.logger.debug2('Query permtags: %s' % res)
        return res

    @transaction
    def __add_perm_tag(self, tag, explain, *args, **kvargs):
        """Add permission tag and entity association.

        :param tag: tag
        :param explain: tag explain
        :param entity: entity id
        :param type: entity type
        :return: True
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # create permtag
        tagrecord = PermTag(tag, explain=explain)
        session.add(tagrecord)
        self.logger.debug2('Add permtag %s' % tagrecord)


    @transaction
    def __add_perm_tag_entity(self, tag, explain, entity, type, *args, **kvargs):
        """Add permission tag and entity association.

        :param tag: tag
        :param explain: tag explain
        :param entity: entity id
        :param type: entity type
        :return: True
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        try:
            tagrecord = session.query(PermTag).filter_by(value=tag).first()
        except:
            self.logger.debug2('Permtag %s does not exist' % tag)
        try:
            record = PermTagEntity(tagrecord.id, entity, type)
            session.add(record)
            self.logger.debug2('Add permtag %s entity %s association' % (tag, entity))
        except:
            self.logger.debug2('Permtag %s entity %s association already exists' % (tag, entity))

        return tagrecord

    def add_perm_tag(self, tag, explain, entity, type, *args, **kvargs):
        """Add permission tag and entity association.

        :param tag: tag
        :param explain: tag explain
        :param entity: entity id
        :param type: entity type
        :return: True
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        try:
            self.__add_perm_tag(tag, explain, *args, **kvargs)
        except:
            self.logger.warning('Permtag %s already exists' % tag)

        tagrecord = self.__add_perm_tag_entity(tag, explain, entity, type, *args, **kvargs)
        # session = self.get_session()
        #
        # try:
        #     # create permtag
        #     session.begin_nested()
        #     tagrecord = PermTag(tag, explain=explain)
        #     session.add(tagrecord)
        #     session.flush()
        #     self.logger.debug2('Add permtag %s' % tagrecord)
        # except:
        #     # permtag already exists. Get reference
        #     self.logger.warning('Permtag %s already exists' % tagrecord)
        #     session.rollback()
        #     tagrecord = session.query(PermTag).filter_by(value=tag).first()
        #
        # # create tag entity association
        # # record = None
        # session.commit()
        # try:
        #     record = PermTagEntity(tagrecord.id, entity, type)
        #     session.add(record)
        #     self.logger.debug2('Add permtag %s entity %s association' % (tag, entity))
        # except:
        #     self.logger.debug2('Permtag %s entity %s association already exists' % (tag, entity))

        return tagrecord

    @transaction
    def delete_perm_tag(self, entity, etype, tags):
        """Remove permission tag entity association.

        :param entity: entity id
        :param etype: entity type
        :param tags: list of associated permission tags
        :return: True
        :rtype: bool
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # remove tag entity association
        items = session.query(PermTagEntity).filter_by(entity=entity).filter_by(type=etype).all()
        for item in items:
            session.delete(item)
        session.flush()
        self.logger.debug2('Delete tag entity %s.%s association' % (entity, etype))

        # remove unused tag
        for tag in tags:
            tagrecord = session.query(PermTag).filter_by(value=tag).first()
            if tagrecord is not None:
                tagusage = session.query(func.count(PermTagEntity.id)).filter_by(tag=tagrecord.id).scalar()
                if tagusage > 0:
                    self.logger.warning('Tag %s is used by other entities' % tag)
                else:
                    session.delete(tagrecord)
                    self.logger.debug2('Delete tag %s' % tag)

        return True
