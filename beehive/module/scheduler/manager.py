'''
Created on Nov 3, 2015

@author: darkbk
'''
import logging
from celery import Celery
from celery.utils.log import get_task_logger
from beehive.common.apimanager import ApiManager
from beecell.logger.helper import LoggerHelper
from signal import SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT
from signal import signal
from datetime import timedelta

logger = get_task_logger(__name__)
logger_level = logging.DEBUG

task_manager = Celery('tasks')
task_scheduler = Celery('scheduler')

def configure_task_manager(broker_url, result_backend, tasks=[], expire=60*60*24):
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
        CELERY_TASK_RESULT_EXPIRES=60,
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
        CELERYD_LOG_FORMAT="[%(asctime)s: %(levelname)s/%(process)s:%(thread)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        CELERYD_TASK_LOG_FORMAT="[%(asctime)s: %(levelname)s/%(process)s:%(thread)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        #CELERYD_TASK_LOG_FORMAT="[%(asctime)s: %(levelname)s/%(process)s:%(thread)s] - [%(task_name)s(%(task_id)s)] - %(message)s"
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
    frmt = "[%(asctime)s: %(levelname)s/%(process)s:%(thread)s] " \
           "%(name)s:%(funcName)s:%(lineno)d - %(message)s"    
    
    log_path = u'/var/log/%s/%s' % (params[u'api_package'], 
                                    params[u'api_env'])
    run_path = u'/var/run/%s/%s' % (params[u'api_package'], 
                                    params[u'api_env'])    
    
    loggers = [logging.getLogger('beehive.common.event')]
    LoggerHelper.rotatingfile_handler(loggers, logger_level, 
                                      '%s/%s.event.log' % (log_path, logname),
                                      frmt=frmt)    
    
    # base logging
    loggers = [logging.getLogger('beehive'),
               logging.getLogger('beehive.db'),
               logging.getLogger('gibboncloud'),
               logging.getLogger('beecell'),
               logging.getLogger('beedrones'),
               logging.getLogger('proxmoxer'),
               logging.getLogger('requests')]
    LoggerHelper.rotatingfile_handler(loggers, logger_level, 
                                      '%s/%s.log' % (log_path, logname),
                                      frmt=frmt)

    # transaction and db logging
    loggers = [logging.getLogger('beehive.util.data'),
               logging.getLogger('sqlalchemy.engine'),
               logging.getLogger('sqlalchemy.pool')]
    LoggerHelper.rotatingfile_handler(loggers, logger_level, 
                                      '%s/%s.db' % (log_path, logname))
    
    # performance logging
    loggers = [logging.getLogger('beecell.perf'), 
               logging.getLogger('beecell.perf')]
    LoggerHelper.rotatingfile_handler(loggers, logger_level, 
                                      '%s/%s.watch' % (log_path, logname), 
                                      frmt='%(asctime)s - %(message)s')

    api_manager = ApiManager(params)
    api_manager.configure()
    api_manager.register_modules()
    #worker = ProcessEventConsumerRedis(api_manager)
    #from beehive.module.tasks import task_manager
    task_manager.api_manager = api_manager

    configure_task_manager(params['broker_url'], params['result_backend'],
                           tasks=params['task_module'], expire=params['expire'])
    
    logger_file = '%s/%s.log' % (log_path, logname)
    argv = ['',
            '--loglevel=%s' % logging.getLevelName(logger_level),
            #'--pool=prefork',
            '--pool=gevent',
            #'--time-limit=600',
            #'--soft-time-limit=300',
            '--maxtasksperchild=100',
            '--autoscale=10,2',
            '--logfile=%s' % logger_file,
            '--pidfile=%s/%s.task.pid' % (run_path, logname)]
    
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
    logger_file = '%s/%s.scheduler.log' % (log_path, params[u'api_id'])
    logger_names = ['gibbon.cloudapi']
    
    for logger_name in logger_names:
        logger = logging.getLogger(logger_name)
        LoggerHelper.rotatingfile_handler([logger], logger_level, logger_file)
        #LoggerHelper.setup_simple_handler(logger, logger_level)

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