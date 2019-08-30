# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import logging
from time import time

from sqlalchemy import create_engine, exc
from sqlalchemy.ext.declarative import declarative_base
from beehive.common.data import operation, query, transaction
from beecell.simple import truncate, encrypt_data, decrypt_data, id_gen
from beecell.db import ModelError, QueryError
from datetime import datetime
import hashlib
from uuid import uuid4
from re import match
from sqlalchemy.dialects import mysql

Base = declarative_base()

logger = logging.getLogger(__name__)


from sqlalchemy import *
from sqlalchemy.schema import DDLElement 
from sqlalchemy.ext import compiler


class CreateView(DDLElement):
    def __init__(self, name, selectable):
        self.name = name
        self.selectable = selectable


class DropView(DDLElement):
    def __init__(self, name):
        self.name = name


@compiler.compiles(CreateView)
def compile_create_view(element, compiler, **kw):
    return "CREATE OR REPLACE VIEW %s AS %s" % (
        element.name, 
        compiler.sql_compiler.process(element.selectable))


@compiler.compiles(DropView)
def compile_drop_view(element, compiler, **kw):
    return "DROP VIEW IF EXISTS %s" % (element.name)


def view(name, metadata, selectable=None, sql=None):
    t = table(name)

    for c in selectable.c:
        c._make_proxy(t)

    CreateView(name, selectable).execute_at('after-create', metadata)
    
    DropView(name).execute_at('before-drop', metadata)
    return t


class AuditData(object):
    """
        Column of common audit
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
    """
        
    """
    __table_args__ = {u'mysql_engine': u'InnoDB'}

    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), unique=True)
    objid = Column(String(400))
    name = Column(String(100), unique=True)
    desc = Column(String(255))
    active = Column(Boolean())
    
    def __init__(self, objid, name, desc=u'', active=True):
        self.uuid = str(uuid4())
        self.objid = objid
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
        filters=[]
        # id is unique
        filters.append(PaginatedQueryGenerator.get_sqlfilter_by_field(u'id', kvargs))
        filters.append(PaginatedQueryGenerator.get_sqlfilter_by_field(u'uuid', kvargs))
        filters.append(PaginatedQueryGenerator.get_sqlfilter_by_field(u'objid', kvargs))
        filters.append(PaginatedQueryGenerator.get_sqlfilter_by_field(u'name', kvargs))
        filters.append(PaginatedQueryGenerator.get_sqlfilter_by_field(u'desc', kvargs))
        filters.append(PaginatedQueryGenerator.get_sqlfilter_by_field(u'active', kvargs))

        # expired
        if u'filter_expired' in kvargs and kvargs.get(u'filter_expired') is not None: 
            if kvargs.get(u'filter_expired') is True:
                filters.append(u' AND t3.expiry_date<=:filter_expiry_date')
            else:
                filters.append(u' AND (t3.expiry_date>:filter_expiry_date OR t3.expiry_date is null)')
        
        # creation_date
        currField = u'filter_creation_date_start'
        if currField in kvargs and kvargs.get(currField) is not None: 
            filters.append(u' AND t3.creation_date>=:{field}'.format(field=currField))
        
        currField = u'filter_creation_date_stop'
        if currField in kvargs and kvargs.get(currField) is not None: 
            filters.append(u' AND t3.creation_date<=:{field}'.format(field=currField))
            
        # modification_date
        currField = u'filter_modification_date_start'
        if currField in kvargs and kvargs.get(currField) is not None: 
            filters.append(u' AND t3.modification_date>=:{field}'.format(field=currField))
        
        currField = u'filter_modification_date_stop'
        if currField in kvargs and kvargs.get(currField) is not None: 
            filters.append(u' AND t3.modification_date<=:{field}'.format(field=currField))
        
        # expiry_date
        currField = u'filter_expiry_date_start'
        if currField in kvargs and kvargs.get(currField) is not None: 
            filters.append(u' AND (t3.expiry_date is null OR t3.expiry_date>=:{field})'.format(field=currField))
        
        currField = u'filter_expiry_date_stop'
        if currField in kvargs and kvargs.get(currField) is not None: 
            filters.append(u' AND (t3.expiry_date is null OR t3.expiry_date<=:{field})'.format(field=currField))
        
        return filters  

    def is_active(self):
        res = (self.active is True or self.active == 1) and self.expiry_date is None
        return res
        # return self.active is True or (self.expiry_date is None or self.expiry_date < datetime.today())
    
    def disable(self):
        self.expiry_date = datetime.today()
        self.name += u'%s-DELETED' % id_gen()
        self.active = False
        
    def __repr__(self):
        return u'<%s id=%s, uuid=%s, obid=%s, name=%s, active=%s>' % (
            self.__class__.__name__, self.id, self.uuid, self.objid, self.name, self.active)
     

class PermTag(Base):
    __tablename__ = u'perm_tag'
    __table_args__ = {u'mysql_engine': u'InnoDB'}
    
    id = Column(Integer, primary_key=True)
    value = Column(String(100), unique = True)
    explain = Column(String(400))
    creation_date = Column(DateTime())
    
    def __init__(self, value, explain=None):
        """Create new permission tag
        
        :param value: tag value
        """
        self.creation_date = datetime.today()
        self.value = value
        self.explain = explain
    
    def __repr__(self):
        return u'<PermTag(%s, %s)>' % (self.value, self.explain)


class PermTagEntity(Base):
    __tablename__ = u'perm_tag_entity'
    __table_args__ = {u'mysql_engine': u'InnoDB'}
    
    id = Column(Integer, primary_key=True)
    tag = Column(Integer)
    entity = Column(Integer)
    type = Column(String(200))
    
    __table_args__ = (
        Index(u'idx_tag_entity', u'tag', u'entity', unique=True),
    )    
    
    def __init__(self, tag, entity, type):
        """Create new permission tag entity association
        
        :param tag: tag id
        :param entity: entity id
        :param type: entity type
        """
        self.tag = tag
        self.entity = entity
        self.type = type
    
    def __repr__(self):
        return u'<PermTagEntity(%s, %s, %s, %s)>' % (self.id, self.tag, 
                                                     self.entity, self.type)


class PaginatedQueryGenerator(object):
    def __init__(self, entity, session, other_entities=[], custom_select=None, with_perm_tag=True):
        """Use this class to generate and configure query with pagination
        and filtering based on tagged entity.
        Base table : perm_tag t1, perm_tag_entity t2, {entitytable} t3
        
        :param entity: main mapper entity
        :param other_entities: other mapper entities [optional] [default=[]]
        :param custom_select: custom select used instead of entity table
        :param with_perm_tag: check permission tags.
        """
        self.logger = logging.getLogger(self.__class__.__module__+ u'.' + self.__class__.__name__)
        
        self.session = session
        self.entity = entity
        self.custom_select = custom_select
        self.other_entities = other_entities
        self.other_tables = []
        self.other_filters = []
        self.filter_fields = []
        self.select_fields = [u't3.*']
        self.with_perm_tag = with_perm_tag
        self.joins = []
    
    def set_pagination(self, page=0, size=10, order=u'DESC', field=u'id'):
        """Set pagiantion params
        
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        """
        if field == u'id':
            field = u't3.id'

        self.page = page
        self.size = size
        self.order = order
        self.field = field
        self.start = str(size * page)
        self.end = str(size * (page + 1))
    
    def add_table(self, table, alias):
        """Append table to query
        
        :param str table: table name
        :param str alias: table alias
        """
        self.other_tables.append([table, alias])

    def add_join(self, table, alias, on, left=False, inner=False, outer=False):
        """Append join to query

        :param str table: table name
        :param str alias: table alias
        :param str on: join on clause
        :param bool left: if True create a left join
        :param bool inner: if True create an inner join
        :param bool outer: if True create an outer join
        """
        join = u'join %s %s on %s' % (table, alias, on)
        if inner is True:
            join = u'inner ' + join
        elif outer is True:
            join = u'outer ' + join
        if left is True:
            join = u'left ' + join
        self.joins.append(join)

    def add_select_field(self, field):
        """Append field to add after SELECT
        
        :param str field: field with syntax <table_ alias>.<field>
        """
        self.select_fields.append(field)             
    
    def add_filter_by_field(self, field, kvargs, custom_filter=None):
        """Add where condition like AND t3.<field>=:<field> if <field> in kvargs
        and not None. If you want a different filter syntax use custom_filter.
        
        :param field: field to search in kvargs
        :param kvargs: query custom params
        :param custom_filter: custom string filter [optional]
        """
        if field in kvargs and kvargs.get(field) is not None:
            if custom_filter is None:    
                self.other_filters.append(u'AND t3.{field}=:{field}'.format(field=field))
            else:
                self.other_filters.append(custom_filter)
    
    @staticmethod
    def get_sqlfilter_by_field(field, kvargs, op=u' AND'):
        """Add where condition like 
            AND t3.<field>=:<field> 
        if <field> in kvargs and not None..
        
        :param field: field to search in kvargs
        :param kvargs: query custom params
        :param filter: sql filters 
        """
        
        if field in kvargs and kvargs.get(field) is not None: 
            return PaginatedQueryGenerator.create_sqlfilter(field, opLogical=op)
        else:
            return u''
    
    @staticmethod
    def create_sqlfilter(param, column=None, opLogical=u' AND', opComparison=u'=', alias=u't3'):
        """create sql where condition filter like 
            AND t3.<field>=:<field> 
        if <field> in kvargs and not None..
        
        :param column: column to search in kvargs
        :param param: query custom params
        :param str filter: sql filters 
        """
                 
        if column is None:
            column = param
 
        if column is not None: 
            return u' {opLogical} {alias}.{column}{opComparison}:{param}'.format(
                column=column, param=param, opLogical=opLogical, opComparison=opComparison, alias=alias)
        else:
            return u''

    def add_filter(self, sqlfilter):
        """Append filter to query
        
        :param str sqlfilter: sql filter like 'AND t3.id=101'
        """
        self.other_filters.append(sqlfilter)
        
    def add_relative_filter(self, sqlfilter, field_name, kvargs):
        """Append filter to query
        
        :param str sqlfilter: sql filter like 'AND t3.id=101'
        :param field_name: name of the field used in filter
        :param kvargs: args to parse that contains field
        """
        if field_name in kvargs and kvargs.get(field_name) is not None:
            self.other_filters.append(sqlfilter)

    def base_stmp(self, count=False):
        """Base statement

        :param count: if True return statement for count
        """
        fields = u', '.join(self.select_fields)
        if count is True:
            fields = u'count(distinct {field}) as count'.format(field=self.field)

        sql = [u'SELECT {fields}', u'FROM {table} t3']
        if self.with_perm_tag is True:
            sql.extend([
                u', perm_tag t1, perm_tag_entity t2 '
            ])

        # append other tables
        for table in self.other_tables:
            sql.append(u', %s %s' % (table[0], table[1]))

        sql.extend([
            u'WHERE 1=1'
        ])
        # set base where
        if self.with_perm_tag is True:
            sql.extend([
                u'AND t3.id=t2.entity AND t2.tag=t1.id',
                u'AND t1.value IN :tags '
            ])

        # add filters
        for sqlfilter in self.other_filters:
            sql.append(sqlfilter)

            # set group by and limit
        if count is False:
            if not hasattr(self.entity, u'__view__') and self.with_perm_tag is True:
                sql.extend([
                    u'GROUP BY {field}',
                    u'ORDER BY {field} {order}'
                ])
            else:
                sql.extend([
                    u'ORDER BY {field} {order}'
                ])
            if self.size > 0:
                sql.append(u'LIMIT {start},{size}')
            elif self.size == -1:
                sql.append(u'')
            else:
                sql.append(u'LIMIT 1000')  # num rows

        # format query
        stmp = u' '.join(sql)
        # custom table like select
        if self.custom_select is not None:
            table = self.custom_select
        # table is defined by entity
        else:
            table = u'`%s`' % self.entity.__tablename__
        stmp = stmp.format(table=table, fields=fields, field=self.field, order=self.order, start=self.start,
                           size=self.size)
        # self.logger.debug2(u'query: %s' % stmp)
        return text(stmp)

    def run(self, tags, *args, **kvargs):
        """Make query
        
        :param list tags: list of permission tags
        """
        start = time()

        if self.with_perm_tag is True:
            self.logger.debug2(u'Authorization with permission tags ENABLED')
        else:
            self.logger.debug2(u'Authorization with permission tags DISABLED')

        if tags is None or len(tags) == 0:
            tags = [u'']

        # make query
        if self.size > 0:
            # count all records
            stmp = self.base_stmp(count=True)
            total = self.session.query(u'count').from_statement(stmp).params(tags=tags, **kvargs).first()[0]

        stmp = self.base_stmp()

        # set query entities
        entities = [self.entity]
        entities.extend(self.other_entities)

        query = self.session.query(*entities).from_statement(stmp).params(tags=tags, **kvargs)
        self.logger.debug2(u'stmp: %s' % query.statement.compile(dialect=mysql.dialect()))
        self.logger.debug2(u'kvargs: %s' % truncate(kvargs))
        self.logger.debug2(u'tags: %s' % truncate(tags))
        res = query.all()
        
        if self.size == 0 or self.size == -1:
            total = len(res)

        elapsed = round(time() - start, 3)
        self.logger.debug2(u'Get %ss (total:%s): %s [%s]' % (self.entity.__tablename__, total, truncate(res), elapsed))
        return res, total

    def base_stmp2(self, count=False, limit=1000):
        """Base statement. Change usage respect base_smtp. Use distinct in select and remove group by

        :param count: if True return statement for count
        :param limit: max returned records [default=1000]
        """
        fields = u', '.join(self.select_fields)
        if count is True:
            fields = u'count(distinct {field}) as count'.format(field=self.field)

        sql = [u'SELECT distinct {fields}', u'FROM {table} t3']
        if self.with_perm_tag is True:
            sql.extend([
                u'inner join perm_tag_entity t2 on  t3.id=t2.entity',
                u'inner join perm_tag t1 on t2.tag=t1.id'
            ])

        # append other tables
        for join in self.joins:
            sql.append(join)

        sql.extend([
            u'WHERE 1=1'
        ])

        # set base where
        if self.with_perm_tag is True:
            sql.extend([
                u'AND t1.value IN :tags '
            ])

        # add filters
        for sqlfilter in self.other_filters:
            sql.append(sqlfilter)

        # set group by and limit
        if count is False:
            sql.extend([
                u'ORDER BY {field} {order}'
            ])

            if self.size > 0:
                sql.append(u'LIMIT {start},{size}')
            elif self.size == -1:
                sql.append(u'')
            else:
                sql.append(u'LIMIT %s' % limit)  # num rows

        # format query
        stmp = u' '.join(sql)

        # custom table like select
        if self.custom_select is not None:
            table = self.custom_select

        # table is defined by entity
        else:
            table = u'`%s`' % self.entity.__tablename__
        stmp = stmp.format(table=table, fields=fields, field=self.field, order=self.order, start=self.start,
                           size=self.size)

        # self.logger.debug2(u'query: %s' % stmp)
        return text(stmp)

    def run2(self, tags, *args, **kvargs):
        """Make query. Use base_smtp2

        :param list tags: list of permission tags
        """
        start = time()

        if self.with_perm_tag is True:
            self.logger.debug2(u'Authorization with permission tags ENABLED')
        else:
            self.logger.debug2(u'Authorization with permission tags DISABLED')

        if tags is None or len(tags) == 0:
            tags = [u'']

        # make query
        if self.size > 0:
            # count all records
            stmp = self.base_stmp2(count=True)
            total = self.session.query(u'count').from_statement(stmp).params(tags=tags, **kvargs).first()[0]

        stmp = self.base_stmp2()

        # set query entities
        entities = [self.entity]
        entities.extend(self.other_entities)

        query = self.session.query(*entities).from_statement(stmp).params(tags=tags, **kvargs)
        self.logger.debug2(u'stmp: %s' % query.statement.compile(dialect=mysql.dialect()))
        self.logger.debug2(u'kvargs: %s' % truncate(kvargs))
        self.logger.debug2(u'tags: %s' % truncate(tags))
        res = query.all()

        if self.size == 0 or self.size == -1:
            total = len(res)

        elapsed = round(time() - start, 3)
        self.logger.debug2(u'Get %ss (total:%s): %s [%s]' % (self.entity.__tablename__, total, truncate(res), elapsed))
        return res, total


class AbstractDbManager(object):
    """Abstract db manager
    """
    def __init__(self, session=None):
        self.logger = logging.getLogger(self.__class__.__module__+  u'.' + self.__class__.__name__)
        
        self._session = session

    def __del__(self):
        pass

    def __repr__(self):
        return u"<%s id='%s'>" % (self.__class__.__name__, id(self))

    def get_session(self):
        if self._session is None:
            return operation.session
        else:
            return self._session

    @staticmethod
    def create_table(db_uri):
        """Create all tables in the engine. This is equivalent to "Create Table"
        statements in raw SQL."""
        try:
            engine = create_engine(db_uri)
            engine.execute("SET FOREIGN_KEY_CHECKS=1;")
            Base.metadata.create_all(engine)
            logger.info(u'Create tables on : %s' % (db_uri))
            del engine
        except exc.DBAPIError as e:
            raise Exception(e)
    
    @staticmethod
    def remove_table(db_uri):
        """ Remove all tables in the engine. This is equivalent to "Drop Table"
        statements in raw SQL."""
        try:
            engine = create_engine(db_uri)
            engine.execute("SET FOREIGN_KEY_CHECKS=0;")
            Base.metadata.drop_all(engine)
            logger.info(u'Remove tables from : %s' % (db_uri))
            del engine
        except exc.DBAPIError as e:
            raise Exception(e)

    def print_stmp(self, stmp):
        """Print a query statement

        :param stmp: statement
        """
        self.logger.debug2(u'stmp: %s' % stmp.statement.compile(dialect=mysql.dialect()))
    
    @query
    def count_entities(self, entityclass):
        """Get model entity count.
        
        :return: entity count
        :raises QueryError: raise :class:`QueryError`  
        """
        session = self.get_session()
        res = session.query(entityclass).count()
            
        self.logger.debug2(u'Count %s: %s' % (entityclass.__name__, res))
        return res    

    def print_query(self, func, query, args):
        """Print query

        :param func: function that run the query
        :param query: query to run
        :param args: query args. Use: inspect.getargvalues(inspect.currentframe())
        """
        self.logger.debug2(u'stmp: %s' % query.statement.compile(dialect=mysql.dialect()))
        args = {arg: args.locals[arg] for arg in args.args}
        self.logger.debug2(args)

    def query_entities(self, entityclass, session, oid=None, objid=None, uuid=None, name=None, *args, **kvargs):
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
        # session = self.get_session()
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

        self.logger.debug2(u'stmp: %s' % query.statement.compile(dialect=mysql.dialect()))
        self.logger.debug2(u'kvargs: %s' % kvargs)

        # entity = query.first()
        #
        # if entity is None:
        #     msg = u'No %s found' % entityclass.__name__
        #     self.logger.error(msg)
        #     raise ModelError(msg, code=404)

        return query

    @query
    def exist_entity(self, entityclass, oid, *args, **kvargs):
        """Parse oid and check entity exists

        :param entityclass: entity model class
        :param oid: entity model id or name or uuid
        :param dict kvargs: additional filters [optional]
        :return: True if exists
        """
        session = self.get_session()

        if oid is None:
            raise ModelError(u'%s %s not found' % (oid, entityclass))

        # get obj by uuid
        if match(u'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(oid)):
            search_field = u'uuid'
            entity = self.query_entities(entityclass, session, uuid=oid, *args, **kvargs)
        # get obj by id
        elif match(u'^\d+$', str(oid)):
            search_field = u'id'
            entity = self.query_entities(entityclass, session, oid=oid, *args, **kvargs)
        # get obj by name
        elif match(u'[\-\w\d]+', oid):
            search_field = u'name'
            entity = self.query_entities(entityclass, session, name=oid, **kvargs)

        res = entity.one_or_none()
        resp = True
        if res is None:
            resp = False

        self.logger.debug2(u'Check entity %s by %s exists: %s' % (entityclass.__name__, search_field, resp))
        return resp

    @query
    def get_entity(self, entityclass, oid, for_update=False, *args, **kvargs):
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
            raise ModelError(u'%s %s not found' % (oid, entityclass))

        # get obj by uuid
        if match(u'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(oid)):
            search_field = u'uuid'
            entity = self.query_entities(entityclass, session, uuid=oid, *args, **kvargs)
        # get obj by id
        elif match(u'^\d+$', str(oid)):
            search_field = u'id'
            entity = self.query_entities(entityclass, session, oid=oid, *args, **kvargs)
        # get obj by name
        elif match(u'[\-\w\d]+', oid):
            search_field = u'name'
            entity = self.query_entities(entityclass, session, name=oid, **kvargs)

        res = None
        if for_update:
            res = entity.with_for_update().first() 
        else:
            res = entity.first()

        if entity is None:
            msg = u'No %s found' % entityclass.__name__
            self.logger.error(msg)
            raise ModelError(msg, code=404)

        self.logger.debug2(u'Query entity %s by %s: %s' % (entityclass.__name__, search_field, res))
        return res
    
    # @query
    # def get_entities(self, entityclass, filters, *args, **kvargs):
    #     """Get model entities
    #
    #     :param entityclass: entity model class
    #     :param filters: entity model filters function. Return query with additional filter
    #     :param int oid: entity id. [optional]
    #     :param str objid: entity authorization id. [optional]
    #     :param str uuid: entity uuid. [optional]
    #     :param str name: entity name. [optional]
    #     :param args: custom params
    #     :param kvargs: custom params
    #     :return: list of entityclass
    #     :raises QueryError: raise :class:`QueryError`
    #     """
    #     session = self.get_session()
    #     query = self.query_entities(entityclass, session, *args, **kvargs)
    #     query = filters(query, *args, **kvargs)
    #
    #     # make query
    #     res = query.all()
    #     self.logger.debug2(u'Get %s: %s' % (entityclass.__name__, truncate(res)))
    #     return res
    
    @query
    def get_paginated_entities(self, entity, tags=[], page=0, size=10, order=u'DESC', field=u't3.id', filters=[],
                               tables=[], select_fields=[], custom_select=None, with_perm_tag=True, *args, **kvargs):
        """Get entities associated with some permission tags

        :param with_perm_tag: if False disable control of permission tags [default=True]
        :param tables: sql tables to add (table_name, alias) [optional]
        :param filters: sql filters to apply [optional]
        :param select_fields: list of fields to add to select [optional]
        :param args: custom params
        :param kvargs: custom params        
        :param entity: entity
        :param tags: list of permission tags
        :param name: name [optional]
        :param desc: desc [optional]
        :param names: name like [optional]
        :param active: active [optional]
        :param creation_date: creation_date [optional]
        :param modification_date: modification_date [optional]
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :return: list of entityclass
        :raises QueryError: raise :class:`QueryError`           
        """
        session = self.get_session()
        
        query = PaginatedQueryGenerator(entity, session, with_perm_tag=with_perm_tag, custom_select=custom_select)
        # set tables
        for table, alias in tables:
            query.add_table(table, alias)
        # add select fields
        for item in select_fields:
            query.add_select_field(item)
        # set filters
        # query.add_filter_by_field(u'name', kvargs)
        query.add_filter_by_field(u'name', kvargs, custom_filter=u'AND t3.name like :name')
        query.add_filter_by_field(u'desc', kvargs, custom_filter=u'AND t3.desc like :desc')
        query.add_filter_by_field(u'active', kvargs)
        query.add_filter_by_field(u'creation_date', kvargs)
        query.add_filter_by_field(u'modification_date', kvargs)

        for item in filters:
            query.add_filter(item)
        query.set_pagination(page=page, size=size, order=order, field=field)
        res = query.run(tags, *args, **kvargs)
        return res
    
    @transaction
    def add_entity(self, entityclass, *args, **kvargs):
        """Add an entity.
        
        :param entityclass: entity model class
        :param value: entity value.
        :param desc: desc
        :return: new entity
        :rtype: Oauth2entity
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()
        
        # create entity
        record = entityclass(*args, **kvargs)
        session.add(record)
        session.flush()
        
        self.logger.debug2(u'Add %s: %s' % (entityclass.__name__, truncate(record)))
        return record
    
    @transaction
    def update_entity(self, entityclass, *args, **kvargs):
        """Update entity.

        :param entityclass: entity model class
        :param int oid: entity id. [optional]
        :param kvargs str: date to update. [optional]
        :return: entity oid
        :raises TransactionError: raise :class:`TransactionError`        
        """        
        session = self.get_session()
        
        # get entity
        oid = kvargs.pop(u'oid', None)
        query = self.query_entities(entityclass, session, oid=oid)

        # check entity exists
        entity = query.first()
        if entity is None:
            msg = u'No %s found' % entityclass.__name__
            self.logger.error(msg)
            raise ModelError(msg, code=404)

        for k, v in kvargs.items():
            if v is None:
                kvargs.pop(k)

        # create data dict with update
        kvargs[u'modification_date'] = datetime.today()

        query.update(kvargs)
        session.flush()
            
        self.logger.debug2(u'Update %s %s with data: %s' % (entityclass.__name__, oid, kvargs))
        return oid

    @transaction
    def update_entity_null(self, entityclass, **kvargs):
        """Update entity.

        :param entityclass: entity model class
        :param int oid: entity id. [optional]
        :param kvargs str: date to update. [optional]
        :return: entity
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # get entity
        oid = kvargs.pop(u'oid', None)
        query = self.query_entities(entityclass, session, oid=oid)

        # check entity exists
        entity = query.first()
        if entity is None:
            msg = u'No %s found' % entityclass.__name__
            self.logger.error(msg)
            raise ModelError(msg, code=404)

        # create data dict with update
        kvargs[u'modification_date'] = datetime.today()

        query.update(kvargs)
        session.flush()

        self.logger.debug2(u'UPDATE NULL %s %s with data: %s' % (entityclass.__name__, oid, kvargs))
        return oid

    @transaction
    def remove_entity(self, entityclass, *args, **kvargs):
        """Remove entity.
        
        :param entityclass: entity model class
        :param int oid: entity id. [optional]
        :return: entity
        :raises TransactionError: raise :class:`TransactionError`
        """
        session = self.get_session()

        # get entity
        query = self.query_entities(entityclass, session, **kvargs)

        # check entity exists
        entity = query.first()
        if entity is None:
            msg = u'No %s found' % entityclass.__name__
            self.logger.error(msg)
            raise ModelError(msg, code=404)

        # delete entity
        session.delete(entity)
        
        self.logger.debug2(u'Remove %s %s' % (entityclass.__name__, entity.id))
        return entity.id
    
    #
    # permission tag
    #
    def get_all_valid_objids(self, args):
        """Get a list of authorization ids that map object
        
        :param args: objid split by //
        :return: list of valid objids
        """
        # first item *.*.*.....
        act_obj = [u'*' for i in args]
        objdis = [u'//'.join(act_obj)]
        if args[0] != u'*':
            pos = 0
            for arg in args:
                act_obj[pos] = arg
                objdis.append(u'//'.join(act_obj))
                pos += 1
    
        return objdis    
    
    def hash_from_permission(self, objdef, objid):
        """Get hash from entity permission (objdef, objid)
        
        :param objdef: enitity permission object type definition
        :param objid: enitity permission object id
        """
        perm = u'%s-%s' % (objdef.lower(), objid)
        tag = hashlib.md5(perm).hexdigest()
        #self.logger.debug2(u'tag: %s, per: %s' % (tag, perm))
        return tag

    @transaction
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
        session = self.get_session()

        # try:
        #     # create permtag
        #     tagrecord = PermTag(tag, explain=explain)
        #     session.add(tagrecord)
        #     session.flush()
        #     self.logger.debug2(u'Add permtag %s' % (tagrecord))
        # except:
        #     # permtag already exists. Get reference
        #     self.logger.warn(u'Permtag %s already exists' % (tagrecord))
        #     session.rollback()
        #     tagrecord = session.query(PermTag).filter_by(value=tag).first()

        query = session.query(PermTag).filter_by(value=tag)
        tagrecord = query.one_or_none()
        if tagrecord is None:
            # create permtag
            tagrecord = PermTag(tag, explain=explain)
            session.add(tagrecord)
            session.flush()
            self.logger.debug2(u'Add permtag %s' % tagrecord)
        else:
            self.logger.warn(u'Permtag %s already exists' % tagrecord)

        # create tag entity association
        # record = None
        try:
            record = PermTagEntity(tagrecord.id, entity, type)
            session.add(record)
            self.logger.debug2(u'Add permtag %s entity %s association' % (tag, entity))
        except:
            self.logger.debug2(u'Permtag %s entity %s association already exists' % (tag, entity))
        
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
        self.logger.debug2(u'Delete tag entity %s.%s association' % (entity, etype))
        
        # remove unused tag
        for tag in tags:
            tagrecord = session.query(PermTag).filter_by(value=tag).first()
            if tagrecord is not None:
                tagusage = session.query(func.count(PermTagEntity.id)).filter_by(tag=tagrecord.id).scalar()
                # tagusage = session.query(PermTagEntity).filter_by(tag=tagrecord.id).all()
                # if len(tagusage) > 0:
                if tagusage > 0:
                    self.logger.warn(u'Tag %s is used by other entities' % tag)
                else:
                    session.delete(tagrecord)
                    self.logger.debug2(u'Delete tag %s' % tag)

        return True

    @transaction
    def add(self, entity):
        """

        :param entity:
        :return:
        """
        if entity is None:
            raise QueryError("Error: can't not add None entity")
        
        session = self.get_session()
        session.add(entity)
        session.flush()
        self.logger.debug2(u'Add %s entity %s' % (entity.__class__.__name__, entity))
        return entity
    
    @transaction
    def add_all(self, entities):
        """

        :param entities:
        :return: num of entities 
        """
        if entities is None:
            raise QueryError("Error: can't not add None entity")
        
        session = self.get_session()
        session.add_all(entities)
        session.flush()
        self.logger.debug2(u'Add all %s entity %s' % (entities[0].__class__.__name__, len(entities)))
        return len(entities)
    
    @transaction
    def update(self, entity):
        if entity is None:
            raise QueryError("Error: can't not update None entity")
        
        self.logger.info(u'Update %s entity %s' % (entity.__class__.__name__, entity))
        if isinstance(entity, AuditData):
            entity.modification_date = datetime.now()
        
        session = self.get_session()
        session.merge(entity)
        session.flush()
        self.logger.info(u'Updated')
        return entity   
    
    @transaction
    def bulk_save_objects(self, entities):
        if entities is None:
            raise QueryError("Error: can't not bulk update None entities")
        
        for entity in entities:
            self.logger.debug(u'Update %s entity %s' % (entities.__class__.__name__, entity))
            if isinstance(entity, BaseEntity):
                entity.modification_date = datetime.today()
        
        session = self.get_session()
        session.bulk_save_objects(entities)
        session.flush()
        self.logger.info(u'Bulk updated %s entities' %len(entities))
        return entities   

    @transaction
    def delete(self, entity):
        """Delete entity

        :param entity: entity
        """
        if entity is None:
            raise QueryError("Error: can't not delete None entity")
        
        self.logger.debug2(u'Delete %s entity %s' % (entity.__class__.__name__, entity))
        if isinstance(entity, BaseEntity):
            if entity.is_active():
                entity.disable()
                self.update(entity)
                logger.info(u'Disable entity %s' % entity.id)
            else:
                logger.info(u'Nothing to do on %s !' % entity)
        else:
            self.purge(entity)
            logger.info(u'Purge entity %s' % entity.id)
        return entity
        
    @transaction
    def purge(self, entity):
        """Hard Delete entity

        :param entity: entity
        :return Boolean:
        """
        if entity is None:
            logger.warn(u'Warning: can\'t not purge None entity')
            return entity
        
        session = self.get_session()
        session.delete(entity)
        session.flush()
        logger.debug2(u'Delete %s entity %s' % (entity.__class__.__name__, entity))

    @staticmethod   
    def add_base_entity_filters(query, *args, **kvargs):
        
        # id is unique
        if u'id' in kvargs and kvargs.get(u'id') is not None:
            query = query.filter_by(id=kvargs.get(u'id'))
        # uuid is unique
        if u'uuid' in kvargs and kvargs.get(u'uuid') is not None:
            query = query.filter_by(uuid=kvargs.get(u'uuid')) 
        
        # Non unique filters
        if u'objid' in kvargs and kvargs.get(u'objid') is not None:
            query = query.filter_by(objid=kvargs.get(u'objid'))
        if u'name' in kvargs and kvargs.get(u'name') is not None:
            query = query.filter_by(name=kvargs.get(u'name'))
        if u'desc' in kvargs and kvargs.get(u'desc') is not None:
            query = query.filter_by(desc=kvargs.get(u'desc'))
        if u'active' in kvargs and kvargs.get(u'active') is not None:
            query = query.filter_by(active=kvargs.get(u'active')) 
            
        return query
