"""
Created on Jan 31, 2014

@author: darkbk
"""
from time import time
from functools import wraps
import logging
from uuid import uuid4

import pymysql
from sqlalchemy.exc import IntegrityError, DBAPIError, ArgumentError
from beecell.simple import id_gen, truncate
from beecell.simple import import_class
from beecell.db import TransactionError, QueryError, ModelError
from multiprocessing import current_process
from threading import current_thread
from re import escape
from beecell.logger.helper import ExtendedLogger

logger = ExtendedLogger(__name__)

# container connection
try:
    import gevent
    container = gevent.local.local() #: thread/gevent local container
except:
    import threading
    container = threading.local()

container.connection = None

# beehive operation
try:
    import gevent
    operation = gevent.local.local() #: thread/gevent local operation
except:
    import threading
    operation = threading.local()

operation.id = None #: operation id in uuid4
operation.session = None #: current database session
operation.user = None #: logged user (username, userip, uid)
operation.perms = None #: logged user permission
operation.transaction = None #: transaction id


def transaction2(rollback_throwable=True):
    """Use this decorator to transform a function that contains delete, insert
    and update statement in a transaction.
    if rollback_throwable is false than then commits anyway
    
    Example::
    
        @transaction
        def fn(*args, **kwargs):
            ....
    """
    def wrapper_transaction2(fn):
        
        @wraps(fn)
        def transaction_inner2(*args, **kwargs): #1
            start = time()
            stmp_id = id_gen()
            session = operation.session
            sessionid = id(session)
            
            commit = False
            if operation.transaction is None:
                operation.transaction = id_gen()
                commit = True
                logger.debug2(u'Create transaction %s' % operation.transaction)
            else:
                logger.debug2(u'Use transaction %s' % operation.transaction)
            
            # set distributed transaction id to 0 for single transaction
            try:
                operation.id
            except: 
                operation.id = str(uuid4())
                
            try:
                # format request params
                params = []
                for item in args:
                    params.append(unicode(item))
                for k, v in kwargs.iteritems():
                    params.append(u"'%s':'%s'" % (k, v))
                    
                # call internal function
                res = fn(*args, **kwargs)
                
                if commit is True:
                    session.commit()
                    logger.log(100, u'Commit transaction %s' % operation.transaction)
                    operation.transaction = None
                    
                elapsed = round(time() - start, 4)
                logger.debug2(u'%s.%s - %s - transaction - %s - %s - OK - %s' % (operation.id, stmp_id, sessionid,
                              fn.__name__, params,  elapsed))
                            
                return res
            except ModelError as ex:
                elapsed = round(time() - start, 4)
                logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
                             fn.__name__,  params, elapsed))
                if ex.code not in [409]:
                    # logger.error(ex.desc, exc_info=1)
                    logger.error(ex.desc)

                if rollback_throwable:
                    rollback(session, commit)
                raise TransactionError(ex.desc, code=ex.code)
            except ArgumentError as ex:
                elapsed = round(time() - start, 4)
                logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
                             fn.__name__,  params, elapsed))
                logger.error(ex.message)
    
                if rollback_throwable:
                    rollback(session, commit) 
                    
                raise TransactionError(ex.message, code=400)
            except IntegrityError as ex:
                elapsed = round(time() - start, 4)
                logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
                             fn.__name__,  params, elapsed))
                logger.error(ex.message)
    
                if rollback_throwable:
                    rollback(session, commit)
                raise TransactionError(ex.message, code=409)
            except DBAPIError as ex:
                elapsed = round(time() - start, 4)
                logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
                             fn.__name__,  params, elapsed))
                #logger.error(ex.message, exc_info=1)
                #logger.error(ex.message)
                      
                if rollback_throwable:
                    rollback(session, commit)
                raise TransactionError(ex.message, code=400)
            except TransactionError as ex:
                elapsed = round(time() - start, 4)
                logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
                             fn.__name__,  params, elapsed))
                # logger.error(ex.desc, exc_info=1)
                logger.error(ex.desc)
                if rollback_throwable:
                    rollback(session, commit)
                raise
            except Exception as ex:
                elapsed = round(time() - start, 4)
                logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
                             fn.__name__,  params, elapsed))
                # logger.error(ex, exc_info=1)
                logger.error(ex)
                if rollback_throwable:
                    rollback(session, commit)
                raise TransactionError(ex, code=400)
            finally:
                if not rollback_throwable:
                    if commit is True and operation.transaction is not None:
                        session.commit()
                        logger.log(100, u'Commit transaction on exception %s' % operation.transaction)
                        operation.transaction = None
                    
        return transaction_inner2
    return wrapper_transaction2

def transaction(fn):
    """Use this decorator to transform a function that contains delete, insert
    and update statement in a transaction.
     
    Example::
     
        @transaction
        def fn(*args, **kwargs):
            ....
    """
    @wraps(fn)
    def transaction_inner(*args, **kwargs): #1
        start = time()
        stmp_id = id_gen()
        session = operation.session
        sessionid = id(session)
         
        commit = False
        if operation.transaction is None:
            operation.transaction = id_gen()
            commit = True
            logger.debug2(u'Create transaction %s' % operation.transaction)
        else:
            logger.debug2(u'Use transaction %s' % operation.transaction)
         
        # set distributed transaction id to 0 for single transaction
        try:
            operation.id
        except: 
            operation.id = str(uuid4())
             
        try:
            # format request params
            params = []
            for item in args:
                params.append(unicode(item))
            for k, v in kwargs.iteritems():
                params.append(u"'%s':'%s'" % (k, v))
                 
            # call internal function
            res = fn(*args, **kwargs)
             
            if commit is True:
                session.commit()
                logger.log(100, u'Commit transaction %s' % operation.transaction)
                operation.transaction = None
                 
            elapsed = round(time() - start, 4)
            logger.debug2(u'%s.%s - %s - transaction - %s - %s - OK - %s' % (operation.id, stmp_id, sessionid,
                          fn.__name__, params,  elapsed))
                         
            return res
        except ModelError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
                         fn.__name__,  params, elapsed))
            if ex.code not in [409]:
                # logger.error(ex.desc, exc_info=1)
                logger.error(ex.desc)
             
            rollback(session, commit)
            raise TransactionError(ex.desc, code=ex.code)
        except ArgumentError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
                         fn.__name__,  params, elapsed))
            logger.error(ex.message)
 
            rollback(session, commit)
            raise TransactionError(ex.message, code=400)
        except IntegrityError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
                         fn.__name__,  params, elapsed))
            logger.error(ex.message)
 
            rollback(session, commit)
            raise TransactionError(ex.message, code=409)
        except DBAPIError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
                         fn.__name__,  params, elapsed))
            #logger.error(ex.message, exc_info=1)
            #logger.error(ex.message)
                   
            rollback(session, commit)
            raise TransactionError(ex.message, code=400)
        except TransactionError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
                         fn.__name__,  params, elapsed))
            # logger.error(ex.desc, exc_info=1)
            logger.error(ex.desc)
            rollback(session, commit)
            raise
        except Exception as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
                         fn.__name__,  params, elapsed))
            # logger.error(ex, exc_info=1)
            logger.error(ex)
            rollback(session, commit)
            raise TransactionError(ex, code=400)
 
    return transaction_inner


def rollback(session, status):
    if status is True:
        session.rollback()
        logger.warn(u'Rollback transaction %s' % operation.transaction)
        operation.transaction = None


def query(fn):
    """Use this decorator to transform a function that contains delete, insert
    and update statement in a transaction.
    
    Example::
    
        @query
        def fn(*args, **kwargs):
            ....    
    """
    @wraps(fn)
    def query_inner(*args, **kwargs): #1
        start = time()
        stmp_id = id_gen()
        session = operation.session
        sessionid = id(session)
        
        # set distributed transaction id to 0 for single transaction
        try:
            operation.id
        except: 
            operation.id = str(uuid4())
        
        try:
            # get runtime info
            cp = current_process()
            ct = current_thread()            
            
            # format request params
            params = []
            for item in args:
                params.append(str(item))
            for k, v in kwargs.iteritems():
                params.append(u"'%s':'%s'" % (k, v))
                
            # call internal function
            res = fn(*args, **kwargs)
            elapsed = round(time() - start, 4)
            logger.debug2(u'%s.%s - %s - query - %s - %s - OK - %s' % (operation.id, stmp_id, sessionid, fn.__name__,
                          truncate(params),  elapsed))
            return res
        except ModelError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - query - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid, fn.__name__,
                         truncate(params), elapsed))
            # logger.error(ex.desc, exc_info=1)
            logger.error(ex.desc)
            raise QueryError(ex.desc, code=ex.code)
        except ArgumentError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - query - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid, fn.__name__,
                         truncate(params), elapsed))
            logger.error(ex.message)
            raise QueryError(ex.message, code=400)
        except DBAPIError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - query - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid, fn.__name__,
                         truncate(params), elapsed))
            # logger.error(ex.message, exc_info=1)
            logger.error(ex.message)
            raise QueryError(ex.message, code=400)
        except TypeError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - query - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid, fn.__name__,
                         truncate(params), elapsed))
            logger.error(ex.message)
            raise QueryError(ex.message, code=400)
        except Exception as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - query - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid, fn.__name__,
                         truncate(params), elapsed))
            logger.error(ex.message)
            raise QueryError(ex.message, code=400)
    return query_inner


def trace(entity=None, op=u'view'):
    """Use this decorator to send an event after function execution.
    
    :param entity: beehive authorized entity [optional]
    :param op: operation. Can be <operation>.view|insert|update|delete|use|*
        <operation>. is optional
    
    Example::
    
        @trace(entity=Role, op=u'view')
        def fn(*args, **kwargs):
            ....    
    """
    def wrapper(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):
            # get start time
            start = time()
            
            args = list(args)            
            inst = args.pop(0)  
            
            def get_entity(entity):
                if entity is None:
                    return inst
                else:
                    eclass = import_class(u'%s.%s' % (inst.__module__, entity))
                    return eclass(inst)

            # execute inner function
            try:
                ret = fn(inst, *args, **kwargs)
            
                # calculate elasped time
                elapsed = round(time() - start, 4)
                get_entity(entity).send_event(op, args=args, params=kwargs, elapsed=elapsed)
            except Exception as ex:
                logger.error(ex)
                # calculate elasped time
                elapsed = round(time() - start, 4)
                ex_escaped = escape(str(ex.message))
                get_entity(entity).send_event(op, args=args, params=kwargs, exception=ex_escaped, elapsed=elapsed)
                raise
            return ret
        return decorated
    return wrapper
