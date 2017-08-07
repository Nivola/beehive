'''
Created on Jan 31, 2014

@author: darkbk
'''
from time import time
from functools import wraps
import logging
from uuid import uuid4
from sqlalchemy.exc import IntegrityError, DBAPIError
from beecell.simple import id_gen
from beecell.simple import get_member_class, import_class
from beecell.db import TransactionError, QueryError, ModelError
from multiprocessing import current_process
from threading import current_thread

logger = logging.getLogger(__name__)

# container connection
try:
    import gevent
    container = gevent.local.local()
except:
    import threading
    container = threading.local()

container.connection = None

# beehive operation
try:
    import gevent
    operation = gevent.local.local()
except:
    import threading
    operation = threading.local()

operation.id = None # uuid4
operation.session = None
operation.user = None # (username, userip, uid)
operation.perms = None

operation.transaction = None


def netsted_transaction(fn):
    """Use this decorator to transform a function that contains delete, insert
    and update statement in a transaction.
    """
    @wraps(fn)
    def netsted_transaction_inner(*args, **kwargs): #1
        start = time()
        stmp_id = id_gen()
        session = operation.session
        sessionid = id(session)
        
        commit = False
        if operation.transaction is None:
            operation.transaction = id_gen()
            commit = True
            logger.debug(u'Create transaction %s' % operation.transaction)
        else:
            logger.debug(u'Use transaction %s' % operation.transaction)
        
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
                params.append(unicode(item))
            for k,v in kwargs.iteritems():
                params.append(u"'%s':'%s'" % (k, v))
                
            # call internal function
            res = fn(*args, **kwargs)
            
            if commit is True:
                session.commit()
                logger.debug(u'Commit transaction %s' % operation.transaction)
                operation.transaction = None
                
            elapsed = round(time() - start, 4)
            logger.debug(u'%s.%s - %s - transaction - %s - %s - OK - %s' % (
                         operation.id, stmp_id, sessionid, fn.__name__, 
                         params,  elapsed))
                        
            return res
        except ModelError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (
                         operation.id, stmp_id, sessionid, fn.__name__, 
                         params, elapsed))
            if ex.code not in [409]:
                logger.error(ex.desc, exc_info=1)
                logger.error(ex.desc)
            
            #session.rollback()
            rollback(session, commit)
            raise TransactionError(ex.desc, code=ex.code)
        except IntegrityError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (
                         operation.id, stmp_id, sessionid, fn.__name__, 
                         params, elapsed))
            logger.error(ex.orig, exc_info=1)
            logger.error(ex.orig)

            #session.rollback()
            rollback(session, commit)
            raise TransactionError(ex.orig)
        except DBAPIError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (
                         operation.id, stmp_id, sessionid, fn.__name__, 
                         params, elapsed))
            logger.error(ex.orig, exc_info=1)
            logger.error(ex.orig)
                  
            #session.rollback()
            rollback(session, commit)
            raise TransactionError(ex.orig)
        except TransactionError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (
                         operation.id, stmp_id, sessionid, fn.__name__, 
                         params, elapsed))
            logger.error(ex.orig, exc_info=1)
            logger.error(ex.orig)
                  
            #session.rollback()
            rollback(session, commit)
            raise
        except Exception as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (
                         operation.id, stmp_id, sessionid, fn.__name__, 
                         params, elapsed))
            logger.error(ex, exc_info=1)
            logger.error(ex)
        
            #session.rollback()
            rollback(session, commit)
            raise TransactionError(ex)

    return netsted_transaction_inner

def rollback(session, status):
    if status is True:
        session.rollback()
        logger.warn(u'Rollback transaction %s' % operation.transaction)
        operation.transaction = None        

def transaction(fn):
    """Use this decorator to transform a function that contains delete, insert
    and update statement in a transaction.
    """
    @wraps(fn)
    def transaction_inner(*args, **kwargs): #1
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
                params.append(unicode(item))
            for k,v in kwargs.iteritems():
                params.append(u"'%s':'%s'" % (k, v))
                
            # call internal function
            res = fn(*args, **kwargs)
            
            session.commit()
            elapsed = round(time() - start, 4)
            logger.debug(u'%s.%s - %s - transaction - %s - %s - OK - %s' % (
                         operation.id, stmp_id, sessionid, fn.__name__, 
                         params,  elapsed))
                        
            return res
        except ModelError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (
                         operation.id, stmp_id, sessionid, fn.__name__, 
                         params, elapsed))
            if ex.code not in [409]:
                #logger.error(ex.desc, exc_info=1)
                logger.error(ex.desc)
                              
            session.rollback()
            raise TransactionError(ex.desc, code=ex.code)
        except IntegrityError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (
                         operation.id, stmp_id, sessionid, fn.__name__, 
                         params, elapsed))
            logger.error(ex.orig, exc_info=1)
            logger.error(ex.orig)

            session.rollback()
            raise TransactionError(ex.orig)
        except DBAPIError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (
                         operation.id, stmp_id, sessionid, fn.__name__, 
                         params, elapsed))
            #logger.error(ex.orig, exc_info=1)
            logger.error(ex.orig)
                  
            session.rollback()
            raise TransactionError(ex.orig)
        
        except Exception as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (
                         operation.id, stmp_id, sessionid, fn.__name__, 
                         params, elapsed))
            #logger.error(ex, exc_info=1)
            logger.error(ex)
        
            session.rollback()
            raise TransactionError(ex)

    return transaction_inner

def query(fn):
    """Use this decorator to transform a function that contains delete, insert
    and update statement in a transaction.
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
            for k,v in kwargs.iteritems():
                params.append(u"'%s':'%s'" % (k, v))
                
            # call internal function
            res = fn(*args, **kwargs)
            elapsed = round(time() - start, 4)
            logger.debug(u'%s.%s - %s - query - %s - %s - OK - %s' % (
                         operation.id, stmp_id, sessionid, fn.__name__, 
                         params,  elapsed))          
            return res
        except ModelError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - query - %s - %s - KO - %s' % (
                         operation.id, stmp_id, sessionid, fn.__name__, 
                         params, elapsed))
            logger.error(ex.desc, exc_info=1)
            logger.error(ex.desc)
            raise QueryError(ex.desc, code=ex.code)    
        except DBAPIError as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - query - %s - %s - KO - %s' % (
                         operation.id, stmp_id, sessionid, fn.__name__, 
                         params, elapsed))
            logger.error(ex.orig, exc_info=1)
            logger.error(ex.orig)
            raise QueryError(ex.orig, code=400)
        except Exception as ex:
            elapsed = round(time() - start, 4)
            logger.error(u'%s.%s - %s - query - %s - %s - KO - %s' % (
                         operation.id, stmp_id, sessionid, fn.__name__, 
                         params, elapsed))
            logger.error(ex, exc_info=1)
            logger.error(ex)

            raise QueryError(ex, code=400)
    return query_inner

def trace(entity=None, op=u'view'):
    """Decorator
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
                get_entity(entity).send_event(op, args=args, params=kwargs, 
                                      elapsed=elapsed)
            except Exception as ex:
                # calculate elasped time
                elapsed = round(time() - start, 4)
                get_entity(entity).send_event(op, args=args, params=kwargs, 
                                      exception=ex, elapsed=elapsed)
                raise
            return ret
        return decorated
    return wrapper

def trace1(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # get start time
        start = time()
        
        args = list(args)            
        inst = args.pop(0)
        
        try:
            op = fn.func_defaults[-1]
        except:
            op = u'view'
        if isinstance(op, tuple):
            op = op[1]
            entity = op[0]
            entity_obj = entity(inst)
        else:
            op = op
            entity_obj = inst

        # execute inner function
        try:
            ret = fn(inst, *args, **kwargs)
        
            # calculate elasped time
            elapsed = round(time() - start, 4)
            entity_obj.send_event(op, args=args, params=kwargs, 
                                  elapsed=elapsed)
        except Exception as ex:
            entity_obj.send_event(op, args=args, params=kwargs, 
                                  exception=ex, elapsed=elapsed)
            raise
        
        return ret
    return wrapper
    