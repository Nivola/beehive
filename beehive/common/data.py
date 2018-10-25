"""
Created on Jan 31, 2014

@author: darkbk
"""
from time import time
from functools import wraps
from uuid import uuid4
from sqlalchemy.exc import IntegrityError, DBAPIError, ArgumentError
from beecell.simple import id_gen, truncate
from beecell.simple import import_class
from beecell.simple import encrypt_data as simple_encrypt_data
from beecell.simple import decrypt_data as simple_decrypt_data
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
operation.token_type = None #: token type released
operation.transaction = None #: transaction id
operation.encryption_key = None #: _encryption_key used to encrypt and decrypt data


#
# encryption method
#
def encrypt_data(data):
    """Encrypt data using a fernet key and a symmetric algorithm

    :param data: data to encrypt
    :return: encrypted data
    """
    # fenet = getattr(operation, "encryption_key", "NON DEFINITO")
    # logger.debug2("::::::::::::::Encrypt data %s" % fernet)
    res = simple_encrypt_data(operation.encryption_key, data)
    logger.debug(u'Encrypt data')
    return res


def decrypt_data(data):
    """Decrypt data using a fernet key and a symmetric algorithm

    :param data: data to decrypt
    :return: decrypted data
    """
    # fenet = getattr(operation, "encryption_key", "NON DEFINITO")
    # logger.debug2("::::::::::::::Encrypt data %s" % fernet)
    
    res = simple_decrypt_data(operation.encryption_key, data)
    logger.debug(u'Decrypt data')
    return res


#
# decorators
#
def core_transaction(fn, rollback_throwable, *args, **kwargs):
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
            return core_transaction(fn, rollback_throwable, *args, **kwargs)
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
        return core_transaction(fn, True, *args, **kwargs)
#         start = time()
#         stmp_id = id_gen()
#         session = operation.session
#         sessionid = id(session)
#          
#         commit = False
#         if operation.transaction is None:
#             operation.transaction = id_gen()
#             commit = True
#             logger.debug2(u'Create transaction %s' % operation.transaction)
#         else:
#             logger.debug2(u'Use transaction %s' % operation.transaction)
#          
#         # set distributed transaction id to 0 for single transaction
#         try:
#             operation.id
#         except: 
#             operation.id = str(uuid4())
#              
#         try:
#             # format request params
#             params = []
#             for item in args:
#                 params.append(unicode(item))
#             for k, v in kwargs.iteritems():
#                 params.append(u"'%s':'%s'" % (k, v))
#                  
#             # call internal function
#             res = fn(*args, **kwargs)
#              
#             if commit is True:
#                 session.commit()
#                 logger.log(100, u'Commit transaction %s' % operation.transaction)
#                 operation.transaction = None
#                  
#             elapsed = round(time() - start, 4)
#             logger.debug2(u'%s.%s - %s - transaction - %s - %s - OK - %s' % (operation.id, stmp_id, sessionid,
#                           fn.__name__, params,  elapsed))
#                          
#             return res
#         except ModelError as ex:
#             elapsed = round(time() - start, 4)
#             logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
#                          fn.__name__,  params, elapsed))
#             if ex.code not in [409]:
#                 # logger.error(ex.desc, exc_info=1)
#                 logger.error(ex.desc)
#              
#             rollback(session, commit)
#             raise TransactionError(ex.desc, code=ex.code)
#         except ArgumentError as ex:
#             elapsed = round(time() - start, 4)
#             logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
#                          fn.__name__,  params, elapsed))
#             logger.error(ex.message)
#  
#             rollback(session, commit)
#             raise TransactionError(ex.message, code=400)
#         except IntegrityError as ex:
#             elapsed = round(time() - start, 4)
#             logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
#                          fn.__name__,  params, elapsed))
#             logger.error(ex.message)
#  
#             rollback(session, commit)
#             raise TransactionError(ex.message, code=409)
#         except DBAPIError as ex:
#             elapsed = round(time() - start, 4)
#             logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
#                          fn.__name__,  params, elapsed))
#             #logger.error(ex.message, exc_info=1)
#             #logger.error(ex.message)
#                    
#             rollback(session, commit)
#             raise TransactionError(ex.message, code=400)
#         except TransactionError as ex:
#             elapsed = round(time() - start, 4)
#             logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
#                          fn.__name__,  params, elapsed))
#             # logger.error(ex.desc, exc_info=1)
#             logger.error(ex.desc)
#             rollback(session, commit)
#             raise
#         except Exception as ex:
#             elapsed = round(time() - start, 4)
#             logger.error(u'%s.%s - %s - transaction - %s - %s - KO - %s' % (operation.id, stmp_id, sessionid,
#                          fn.__name__,  params, elapsed))
#             # logger.error(ex, exc_info=1)
#             logger.error(ex)
#             rollback(session, commit)
#             raise TransactionError(ex, code=400)
 
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


def trace(entity=None, op=u'view', noargs=False):
    """Use this decorator to send an event after function execution.
    
    :param entity: beehive authorized entity [optional]
    :param op: operation. Can be <operation>.view|insert|update|delete|use|* <operation>. is optional
    :param noargs: if True do not trace command args and kvargs [default=False]
    
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
                if noargs is True:
                    get_entity(entity).send_event(op, args=[], params={}, elapsed=elapsed)
                else:
                    get_entity(entity).send_event(op, args=args, params=kwargs, elapsed=elapsed)
            except Exception as ex:
                logger.error(ex)
                # calculate elasped time
                elapsed = round(time() - start, 4)
                # ex_escaped = escape(str(ex.message))
                ex_escaped = str(ex.message)
                if noargs is True:
                    get_entity(entity).send_event(op, args=[], params={}, exception=ex_escaped, elapsed=elapsed)
                else:
                    get_entity(entity).send_event(op, args=args, params=kwargs, exception=ex_escaped, elapsed=elapsed)
                raise
            return ret
        return decorated
    return wrapper


def maybe_run_batch_greenlet(controller, batch, timeout=600):
    """Use this decorator to run a parallel greenlet if batch is True.

    :param controller: controller instance
    :param batch: if True run a new greenlet
    :param timeout: greenlet timeout

    Example::

        @maybe_run_batch_greenlet(True)
        def action(*args, **kwargs):
            ....
    """
    def wrapper(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):
            # get start time
            start = time()

            logger = controller.logger

            logger.info(u'Outer %s - START' % fn.__name__)

            # execute inner function
            try:
                # encapsulate method
                def inner_fn(user, perms, opid, *args, **kwargs):
                    # get start time
                    start_inner = time()

                    logger.info(u'Inner %s - START' % fn.__name__)

                    try:
                        # set local thread operation
                        operation.user = user
                        operation.perms = perms
                        operation.id = opid
                        operation.transaction = None

                        # open db session
                        controller.get_session()

                        fn(*args, **kwargs)
                        # calculate elasped time
                        elapsed_inner = round(time() - start_inner, 4)
                        logger.info(u'Inner %s - STOP - %s' % (fn.__name__, elapsed_inner))
                        return True
                    except:
                        # calculate elasped time
                        elapsed_inner = round(time() - start_inner, 4)
                        logger.error(u'', exc_info=1)
                        logger.error(u'Inner %s - ERROR - %s' % (fn.__name__, elapsed_inner))
                    finally:
                        controller.release_session()

                    return False

                user = operation.user
                perms = operation.perms
                opid = operation.id
                res = gevent.spawn(inner_fn, user, perms, opid, *args, **kwargs)
                if batch is True:
                    logger.debug(u'Start batch operation: %s' % res)
                else:
                    gevent.joinall([res], timeout=timeout)

                # calculate elasped time
                elapsed = round(time() - start, 4)
                logger.info(u'Outer %s - STOP - %s' % (fn.__name__, elapsed))
            except:
                # calculate elasped time
                elapsed = round(time() - start, 4)
                logger.error(u'', exc_info=1)
                logger.error(u'Outer %s - ERROR - %s' % (fn.__name__, elapsed))
                raise
            return True
        return decorated
    return wrapper
