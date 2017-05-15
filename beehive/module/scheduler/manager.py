'''
Created on Nov 3, 2015

@author: darkbk
'''
import logging
from beecell.logger.helper import LoggerHelper
from signal import SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT
from signal import signal
from datetime import timedelta
from socket import gethostname
from celery.utils.term import colored
from celery.utils.log import ColorFormatter
from celery.app.log import TaskFormatter
from celery import Celery
from celery.utils.log import get_task_logger
from celery._state import get_current_task
import celery.signals
from beehive.common.apimanager import ApiManager

class ExtTaskFormatter(ColorFormatter):
    COLORS = colored().names
    colors = {'DEBUG': COLORS['blue'], 'WARNING': COLORS['yellow'],
              'ERROR': COLORS['red'], 'CRITICAL': COLORS['magenta']}
    
    def format(self, record):
        task = get_current_task()
        if task and task.request:
            name = task.name.split(u'.')[-1]
            record.__dict__.update(task_id=task.request.id,
                                   task_name=name)
        else:
            record.__dict__.update(task_id=u'xxx',
                                   task_name=u'xxx')            
            #record.__dict__.setdefault('task_name', '???')
            #record.__dict__.setdefault('task_id', '???')
        return ColorFormatter.format(self, record)

logger = get_task_logger(__name__)
logger_level = logging.DEBUG

task_manager = Celery('tasks')
task_scheduler = Celery('scheduler')

# setup logging
@celery.signals.setup_logging.connect
def on_celery_setup_logging(**args):
    print args
    
#@celery.signals.after_setup_logger.connect
#def on_celery_after_setup_logger(**args):
#    print args

def configure_task_manager(broker_url, result_backend, tasks=[], 
                           expire=60*60*24, logger_file=None):
    """
    :param broker_url: url of the broker
    :param result_backend: url of the result backend
    :param tasks: list of tasks module. Ex.
                  ['beehive.module.scheduler.tasks',
                   'beehive.module.service.plugins.filesharing',]
    """
    task_manager.conf.update(
        BROKER_URL=broker_url,
        CELERY_RESULT_BACKEND=result_backend,
        CELERY_REDIS_RESULT_KEY_PREFIX='celery-task-meta2-',
        CELERY_REDIS_RESULT_EXPIRES=expire,
        CELERY_TASK_RESULT_EXPIRES=600,
        CELERY_TASK_SERIALIZER='json',
        CELERY_ACCEPT_CONTENT=['json'],  # Ignore other content
        CELERY_RESULT_SERIALIZER='json',
        CELERY_TIMEZONE='Europe/Rome',
        CELERY_ENABLE_UTC=True,
        CELERY_IMPORTS=tasks,
        CELERY_DISABLE_RATE_LIMITS = True,
        CELERY_TRACK_STARTED=True,
        CELERY_CHORD_PROPAGATES=True,
        CELERYD_TASK_TIME_LIMIT=7200,
        CELERYD_TASK_SOFT_TIME_LIMIT=7200,
        #CELERY_SEND_TASK_SENT_EVENT=True,
        #CELERY_SEND_EVENTS=True,
        #CELERY_EVENT_SERIALIZER='json',
        #CELERYD_LOG_FORMAT=u'[%(asctime)s: %(levelname)s/%(processName)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s',
        CELERYD_TASK_LOG_FORMAT=u'[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s:%(task_id)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s'
        #worker_task_log_format=u'[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s:%(task_id)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s'
    )
    return task_manager

def configure_task_scheduler(broker_url, schedule_backend, tasks=[]):
    """
    :param broker_url: url of the broker
    :param schedule_backend: url of the schedule backend where schedule entries 
                             are stored
    :param tasks: list of tasks module. Ex.
                  ['beehive.module.scheduler.tasks',
                   'beehive.module.service.plugins.filesharing',]
    """
    task_scheduler.conf.update(
        BROKER_URL=broker_url,
        CELERY_SCHEDULE_BACKEND=schedule_backend,
        CELERY_REDIS_SCHEDULER_KEY_PREFIX='celery-schedule',        
        CELERY_TASK_SERIALIZER='json',
        CELERY_ACCEPT_CONTENT=['json'],  # Ignore other content
        CELERY_RESULT_SERIALIZER='json',
        CELERY_TIMEZONE='Europe/Rome',
        CELERY_ENABLE_UTC=True,
        #CELERY_IMPORTS=tasks,
        CELERYBEAT_SCHEDULE = {
            'test-every-600-seconds': {
                'task': 'tasks.test',
                'schedule': timedelta(seconds=600),
                'args': ()
            },
        }
    )
    return task_scheduler

def start_task_manager(params):
    """Start celery task manager
    """
    logname = "%s.task" % params['api_id']
    frmt = u'[%(asctime)s: %(levelname)s/%(processName)s] ' \
           u'%(name)s:%(funcName)s:%(lineno)d - %(message)s'
    
    frmt = u'[%(asctime)s: %(levelname)s/%(task_name)s:%(task_id)s] '\
           u'%(name)s:%(funcName)s:%(lineno)d - %(message)s'    
    
    log_path = u'/var/log/%s/%s' % (params[u'api_package'], 
                                    params[u'api_env'])
    run_path = u'/var/run/%s/%s' % (params[u'api_package'], 
                                    params[u'api_env'])    
    
    #loggers = [logging.getLogger('beehive.common.event')]
    #LoggerHelper.rotatingfile_handler(loggers, logger_level, 
    #                                  '%s/%s.event.log' % (log_path, logname),
    #                                  frmt=frmt)    
    
    # base logging
    loggers = [
        logging.getLogger(u'beehive'),
        logging.getLogger(u'beehive.db'),
        logging.getLogger(u'beecell'),
        logging.getLogger(u'beedrones'),
        logging.getLogger(u'celery'),
        logging.getLogger(u'proxmoxer'),
        logging.getLogger(u'requests')]
    LoggerHelper.rotatingfile_handler(loggers, logger_level, 
                                      u'%s/%s.log' % (log_path, logname),
                                      frmt=frmt, formatter=ExtTaskFormatter)

    # transaction and db logging
    loggers = [
        logging.getLogger('beehive.util.data'),
        logging.getLogger('sqlalchemy.engine'),
        logging.getLogger('sqlalchemy.pool')]
    LoggerHelper.rotatingfile_handler(loggers, logger_level, 
                                      '%s/%s.db.log' % (log_path, logname))
    
    # performance logging
    loggers = [
        logging.getLogger('beecell.perf')]
    LoggerHelper.rotatingfile_handler(loggers, logger_level, 
                                      '%s/%s.watch' % (log_path, params[u'api_id']), 
                                      frmt='%(asctime)s - %(message)s')

    api_manager = ApiManager(params, hostname=gethostname())
    api_manager.configure()
    api_manager.register_modules()
    #worker = ProcessEventConsumerRedis(api_manager)
    #from beehive.module.tasks import task_manager
    task_manager.api_manager = api_manager

    logger_file = '%s/%s.log' % (log_path, logname)

    configure_task_manager(params['broker_url'], params['result_backend'],
                           tasks=params['task_module'], expire=params['expire'],
                           logger_file=logger_file)
    
    argv = [u'',
            u'--loglevel=%s' % logging.getLevelName(logger_level),
            #u'--pool=prefork',
            u'--pool=gevent',
            u'--purge',
            #'--time-limit=600',
            #'--soft-time-limit=300',
            u'--concurrency=100',
            u'--maxtasksperchild=100',
            #u'--autoscale=100,10',
            u'--logfile=%s' % logger_file,
            u'--pidfile=%s/%s.task.pid' % (run_path, logname)]
    
    def terminate(*args):
        #run_command(['celery', 'multi', 'stopwait', 'worker1', 
        #             '--pidfile="run/celery-%n.pid"'])
        task_manager.stop()
    
    #for sig in (SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT):
    #    signal(sig, terminate)
    
    task_manager.worker_main(argv)
    
def start_scheduler(params):
    """start celery scheduler """
    log_path = u'/var/log/%s/%s' % (params[u'api_package'], 
                                    params[u'api_env'])
    run_path = u'/var/run/%s/%s' % (params[u'api_package'], 
                                    params[u'api_env'])       
    logger_file = u'%s/%s.scheduler.log' % (log_path, params[u'api_id'])
    loggers = [
        logging.getLogger(u'beehive'),
        logging.getLogger(u'beecell'),
        logging.getLogger(u'beedrones'),
        logging.getLogger(u'celery'),        
    ]

    LoggerHelper.rotatingfile_handler(loggers, logger_level, 
                                      logger_file,
                                      formatter=ExtTaskFormatter)        

    api_manager = ApiManager(params)
    api_manager.configure()
    api_manager.register_modules()
    #worker = ProcessEventConsumerRedis(api_manager)
    #from beehive.module.tasks import task_manager
    task_scheduler.api_manager = api_manager
    
    configure_task_scheduler(params['broker_url'], params['result_backend'])

    #from beehive.module.scheduler.scheduler import RedisScheduler
    from beehive.module.scheduler.redis_scheduler import RedisScheduler

    beat = task_scheduler.Beat(loglevel=logging.getLevelName(logger_level), 
                               logfile='%s/%s.scheduler.log' % (log_path, 
                                                                params['api_id']),
                               pidfile='%s/%s.scheduler.pid' % (run_path, 
                                                                params['api_id']),
                               scheduler_cls=RedisScheduler)

    
    def terminate(*args):
        #run_command(['celery', 'multi', 'stopwait', 'worker1', 
        #             '--pidfile="run/celery-%n.pid"'])
        #beat.Service.stop()
        pass
    
    for sig in (SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT):
        signal(sig, terminate)
    
    beat.run()