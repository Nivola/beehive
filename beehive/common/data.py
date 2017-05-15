'''
Created on Jan 31, 2014

@author: darkbk
'''
from time import time
from functools import wraps
import logging

from sqlalchemy.exc import IntegrityError, DBAPIError
from beecell.simple import id_gen
from beecell.simple import get_member_class
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

# database operation
try:
    import gevent
    operation = gevent.local.local()
except:
    import threading
    operation = threading.local()
    
operation.transaction = None
operation.session = None
operation.user = None # (username, userip, uid)
operation.perms = None

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
            operation.transaction
        except: 
            operation.transaction = 0
            
        try:
            # get runtime info
            cp = current_process()
            ct = current_thread()              
            
            # watch log
            #info = "%s:%s - %s:%s.%s - START" % (cp.ident, ct.ident, 
            #                                     fn.__module__+'.'+get_member_class(args), 
            #                                     fn.func_name, stmp_id)
            #logging.getLogger('beecell.perf').info(info)            
            
            # format request params
            params = []
            for item in args:
                params.append(unicode(item))
            for k,v in kwargs.iteritems():
                params.append("'%s':'%s'" % (k, v))
                
            # call internal function
            res = fn(*args, **kwargs)
            
            session.commit()
            elapsed = round(time() - start, 4)
            logger.debug('%s.%s - %s - TRANSACTION - %s - %s - OK - %s' % (
                         operation.transaction, stmp_id, sessionid, fn.__name__, 
                         params,  elapsed))
            
            # watch log
            #info = "%s:%s - %s:%s.%s - STOP - %s" % (cp.ident, ct.ident, 
            #                                         fn.__module__+'.'+get_member_class(args), 
            #                                         fn.func_name, stmp_id, elapsed)
            #logging.getLogger('beecell.perf').info(info)               
            #return res
        except ModelError as ex:
            elapsed = round(time() - start, 4)
            logger.error('%s.%s - %s - TRANSACTION - %s - %s - KO - %s - %s' % (
                         operation.transaction, stmp_id, sessionid, fn.__name__, 
                         params, ex, elapsed))
            
            # watch log
            #info = "%s:%s - %s:%s.%s - ERROR - %s" % (cp.ident, ct.ident, 
            #                                         fn.__module__+'.'+get_member_class(args), 
            #                                         fn.func_name, stmp_id, elapsed)
            #logging.getLogger('beecell.perf').info(info)
                                       
            session.rollback()
            raise TransactionError(ex.desc, code=ex.code)
        except IntegrityError as ex:
            elapsed = round(time() - start, 4)
            logger.error('%s.%s - %s - TRANSACTION - %s - %s - KO - %s - %s' % (
                         operation.transaction, stmp_id, sessionid, fn.__name__, 
                         params, ex, elapsed))
            
            # watch log
            #info = "%s:%s - %s:%s.%s - ERROR - %s" % (cp.ident, ct.ident, 
            #                                         fn.__module__+'.'+get_member_class(args), 
            #                                         fn.func_name, stmp_id, elapsed)
            #logging.getLogger('beecell.perf').info(info)
                        
            session.rollback()
            raise TransactionError(ex.orig)
        except DBAPIError as ex:
            elapsed = round(time() - start, 4)
            logger.error('%s.%s - %s - TRANSACTION - %s - %s - KO - %s - %s' % (
                         operation.transaction, stmp_id, sessionid, fn.__name__, 
                         params, ex, elapsed))
            
            # watch log
            #info = "%s:%s - %s:%s.%s - ERROR - %s" % (cp.ident, ct.ident, 
            #                                         fn.__module__+'.'+get_member_class(args), 
            #                                         fn.func_name, stmp_id, elapsed)
            #logging.getLogger('beecell.perf').info(info)
                        
            session.rollback()
            raise TransactionError(ex.orig)

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
            operation.transaction
        except: 
            operation.transaction = 0        
        
        try:
            # get runtime info
            cp = current_process()
            ct = current_thread()            
            
            # watch log
            #info = "%s:%s - %s:%s.%s - START" % (cp.ident, ct.ident, 
            #                                     fn.__module__+'.'+get_member_class(args), 
            #                                     fn.func_name, stmp_id)
            #logging.getLogger('beecell.perf').info(info)            
            
            # format request params
            params = []
            for item in args:
                params.append(str(item))
            for k,v in kwargs.iteritems():
                params.append("'%s':'%s'" % (k, v))
                
            # call internal function
            res = fn(*args, **kwargs)
            elapsed = round(time() - start, 4)
            logger.debug('%s.%s - %s - QUERY - %s - %s - OK - %s' % (
                         operation.transaction, stmp_id, sessionid, fn.__name__, 
                         params,  elapsed))
            
            
            # watch log
            #info = "%s:%s - %s:%s.%s - STOP - %s" % (cp.ident, ct.ident, 
            #                                         fn.__module__+'.'+get_member_class(args), 
            #                                         fn.func_name, stmp_id, elapsed)
            #logging.getLogger('beecell.perf').info(info)            
            return res
        except ModelError as ex:
            elapsed = round(time() - start, 4)
            logger.error('%s.%s - %s - query - %s - %s - KO - %s - %s' % (
                         operation.transaction, stmp_id, sessionid, fn.__name__, 
                         params, ex, elapsed))
            
            # watch log
            #info = "%s:%s - %s:%s.%s - ERROR - %s" % (cp.ident, ct.ident, 
            #                                         fn.__module__+'.'+get_member_class(args), 
            #                                         fn.func_name, stmp_id, elapsed)
            #logging.getLogger('beecell.perf').info(info)
            
            raise QueryError(ex.desc, code=ex.code)    
        except DBAPIError as ex:
            elapsed = round(time() - start, 4)
            logger.error('%s.%s - %s - query - %s - %s - KO - %s - %s' % (
                         operation.transaction, stmp_id, sessionid, fn.__name__, 
                         params, ex, elapsed))
            
            # watch log
            #info = "%s:%s - %s:%s.%s - ERROR - %s" % (cp.ident, ct.ident, 
            #                                         fn.__module__+'.'+get_member_class(args), 
            #                                         fn.func_name, stmp_id, elapsed)
            #logging.getLogger('beecell.perf').info(info)
                        
            raise QueryError(ex.orig, code=400)
        except Exception as ex:
            elapsed = round(time() - start, 4)
            logger.error('%s.%s - %s - query - %s - %s - KO - %s - %s' % (
                         operation.transaction, stmp_id, sessionid, fn.__name__, 
                         params, ex, elapsed))
            
            # watch log
            #info = "%s:%s - %s:%s.%s - ERROR - %s" % (cp.ident, ct.ident, 
            #                                         fn.__module__+'.'+get_member_class(args), 
            #                                         fn.func_name, stmp_id, elapsed)
            #logging.getLogger('beecell.perf').info(info)
                        
            raise QueryError(ex, code=400)
    return query_inner