# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

import logging
from beecell.logger.helper import LoggerHelper
from signal import SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT
from signal import signal
from datetime import timedelta
from socket import gethostname
from celery.utils.term import colored
from celery.utils.log import ColorFormatter
from celery import Celery
from celery._state import get_current_task
import celery.signals
from kombu import Exchange, Queue
from beehive.common.apimanager import ApiManager

logger = logging.getLogger(__name__)


class ExtTaskFormatter(ColorFormatter):
    COLORS = colored().names
    colors = {
        'DEBUG': COLORS['blue'],
        'WARNING': COLORS['yellow'],
        'WARN': COLORS['yellow'],
        'ERROR': COLORS['red'],
        'CRITICAL': COLORS['magenta'],
        'DEBUG2': COLORS['green'],
        'DEBUG3': COLORS['cyan']
    }

    def format(self, record):
        task = get_current_task()
        if task and task.request:
            name = task.name.split('.')[-1]
            record.__dict__.update(task_id=task.request.id, task_name=name)
        else:
            record.__dict__.update(task_id='xxx', task_name='xxx')
        return ColorFormatter.format(self, record)


# logger_level = LoggerHelper.DEBUG
internal_logger_level = LoggerHelper.DEBUG

task_manager = Celery('tasks')
task_scheduler = Celery('scheduler')


# setup logging
@celery.signals.setup_logging.connect
def on_celery_setup_logging(**args):
    pass


def configure_task_manager(broker_url, result_backend, tasks=[], expire=60*60*24, task_queue='celery',
                           logger_file=None, time_limit=1200):
    """Configure Task manager

    :param broker_url: url of the broker
    :param result_backend: url of the result backend
    :param tasks: list of tasks module. Ex.
                  ['beehive.module.scheduler.tasks', 'beehive.module.service.plugins.filesharing',]
    """
    # # get redis password
    # redis_password = None
    # if result_backend.find('@') > 0:
    #     redis_password = match(r"redis:\/\/([\w\W\d]*)@.", result_backend).groups()[0]

    task_manager.conf.update(
        BROKER_URL=broker_url,
        BROKER_POOL_LIMIT=20,
        BROKER_HEARTBEAT=20,
        BROKER_CONNECTION_MAX_RETRIES=10,
        TASK_DEFAULT_QUEUE=task_queue,
        TASK_DEFAULT_EXCHANGE=task_queue,
        TASK_DEAFAULT_ROUTING_KEY=task_queue,
        CELERY_QUEUES=(
            Queue(
                task_queue,
                Exchange(task_queue),
                routing_key=task_queue),
        ),
        CELERY_RESULT_BACKEND=result_backend,
        CELERY_REDIS_RESULT_KEY_PREFIX='%s.celery-task-meta2-' % task_queue,
        CELERY_REDIS_RESULT_EXPIRES=expire,
        CELERY_TASK_IGNORE_RESULT=True,
        CELERY_TASK_RESULT_EXPIRES=600,
        CELERY_TASK_SERIALIZER='json',
        CELERY_ACCEPT_CONTENT=['json'],  # Ignore other content
        CELERY_RESULT_SERIALIZER='json',
        CELERY_TIMEZONE='Europe/Rome',
        CELERY_ENABLE_UTC=True,
        CELERY_IMPORTS=tasks,
        CELERY_DISABLE_RATE_LIMITS=True,
        CELERY_TRACK_STARTED=True,
        CELERY_CHORD_PROPAGATES=True,
        CELERYD_TASK_TIME_LIMIT=time_limit,
        CELERYD_TASK_SOFT_TIME_LIMIT=time_limit,
        CELERYD_CONCURRENCY=10,
        CELERYD_POOL='beehive.common.task.task_pool:TaskPool',
        CELERYD_TASK_LOG_FORMAT='[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s:%(task_id)s] '
                                '%(name)s:%(funcName)s:%(lineno)d - %(message)s',
        CELERYD_MAX_TASKS_PER_CHILD=20
    )

    return task_manager


def configure_task_scheduler(broker_url, schedule_backend, tasks=[], task_queue=None):
    """Configure task scheduler

    :param broker_url: url of the broker
    :param schedule_backend: url of the schedule backend where schedule entries
                             are stored
    :param tasks: list of tasks module. Ex.
                  ['beehive.module.scheduler.tasks', 'beehive.module.service.plugins.filesharing',]
    """
    task_scheduler.conf.update(
        CELERY_TASK_DEFAULT_QUEUE=task_queue,
        # CELERY_TASK_DEFAULT_EXCHANGE=task_queue,
        # CELERY_TASK_DEAFAULT_ROUTING_KEY=task_queue,
        BROKER_URL=broker_url,
        CELERY_SCHEDULE_BACKEND=schedule_backend,
        # CELERYBEAT_SCHEDULE_FILENAME='/tmp/celerybeat-schedule',
        # CELERY_REDIS_SCHEDULER_KEY_PREFIX='celery-schedule',
        CELERY_REDIS_SCHEDULER_KEY_PREFIX=task_queue + '.schedule',
        CELERY_TASK_SERIALIZER='json',
        CELERY_ACCEPT_CONTENT=['json'],  # Ignore other content
        CELERY_RESULT_SERIALIZER='json',
        CELERY_TIMEZONE='Europe/Rome',
        CELERY_ENABLE_UTC=True,
        # CELERY_IMPORTS=tasks,
        CELERYBEAT_MAX_LOOP_INTERVAL=5,
        CELERYBEAT_SCHEDULE={
            'test-every-30-minutes': {
                'task': 'beehive.module.scheduler.tasks.test',
                'schedule': timedelta(minutes=30),
                'args': ('*', {}),
                'options': {'queue': task_queue}
            },
        }
    )
    return task_scheduler


def start_task_manager(params):
    """Start celery task manager
    """
    logname = "%s.task" % params['api_id']
    frmt = '[%(asctime)s: %(levelname)s/%(task_name)s:%(task_id)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s'

    log_path = run_path = params.get('api_log', None)
    if log_path is None:
        log_path = '/var/log/%s/%s' % (params['api_package'], params['api_env'])
        run_path = '/var/run/%s/%s' % (params['api_package'], params['api_env'])

    logger_level = int(params['api_logging_level'], logging.DEBUG)

    # base logging
    main_loggers = [
        logging.getLogger('beehive'),
        logging.getLogger('beehive.common.model'),
        logging.getLogger('beehive_service'),
        logging.getLogger('beehive_resource'),
        logging.getLogger('beehive.db'),
        logging.getLogger('beecell'),
        logging.getLogger('beedrones'),
        logging.getLogger('celery'),
        logging.getLogger('proxmoxer'),
        logging.getLogger('requests')
    ]
    LoggerHelper.rotatingfile_handler(main_loggers, logger_level, '%s/%s.log' % (log_path, logname),
                                      frmt=frmt, formatter=ExtTaskFormatter)

    # # transaction and db logging
    # loggers = [
    #     # logging.getLogger('beehive.common.data'),
    #     logging.getLogger('sqlalchemy.engine'),
    #     logging.getLogger('sqlalchemy.pool')
    # ]
    # LoggerHelper.rotatingfile_handler(loggers, logger_level, '%s/%s.db.log' % (log_path, logname))
    #
    # # performance logging
    # loggers = [
    #     logging.getLogger('beecell.perf')
    # ]
    # LoggerHelper.rotatingfile_handler(loggers, logger_level, '%s/%s.watch' % (log_path, params['api_id']),
    #                                   frmt='%(asctime)s - %(message)s')

    # setup api manager
    api_manager = ApiManager(params, hostname=gethostname())
    api_manager.configure()
    api_manager.register_modules(register_api=False)
    task_manager.api_manager = api_manager

    # elk logger
    if api_manager.elasticsearch is not None:
        frmt = '{"timestamp":"%(asctime)s", "levelname":"%(levelname)s", "task_name":"%(task_name)s", ' \
               '"task_id":"%(task_id)s", "module":"%(name)s", "func":"%(funcName)s", "lineno":"%(lineno)d",' \
               '"message":"%(message)s"}'
        tags = []
        LoggerHelper.elastic_handler(main_loggers, logger_level, api_manager.elasticsearch, index='cmp',
                                     frmt=frmt, tags=tags, server=api_manager.server_name, app=api_manager.app_id,
                                     component='task')

    logger_file = '%s/%s.log' % (log_path, logname)

    configure_task_manager(params['broker_url'], params['result_backend'], tasks=params['task_module'],
                           expire=params['expire'], task_queue=params['broker_queue'], logger_file=logger_file,
                           time_limit=params['task_time_limit'])

    argv = [
        '',
        '--hostname=' + params['broker_queue'] + '@%h',
        '--loglevel=%s' % logging.getLevelName(internal_logger_level),
        '--purge',
        '--logfile=%s' % logger_file,
        '--pidfile=%s/%s.pid' % (run_path, logname),
    ]

    def terminate(*args):
        task_manager.stop()

    # for sig in (SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT):
    #    signal(sig, terminate)

    task_manager.worker_main(argv)


def start_scheduler(params):
    """start celery scheduler """
    log_path = run_path = params.get('api_log', None)
    if log_path is None:
        log_path = '/var/log/%s/%s' % (params['api_package'], params['api_env'])
        run_path = '/var/run/%s/%s' % (params['api_package'], params['api_env'])

    logger_file = '%s/%s.scheduler.log' % (log_path, params['api_id'])

    logger_level = logging.INFO
    loggers = [
        logging.getLogger('beehive'),
        logging.getLogger('beecell'),
        logging.getLogger('beedrones'),
        logging.getLogger('celery'),
    ]
    LoggerHelper.rotatingfile_handler(loggers, logger_level, logger_file, formatter=ExtTaskFormatter)

    api_manager = ApiManager(params)
    api_manager.configure()
    api_manager.register_modules()
    task_scheduler.api_manager = api_manager

    configure_task_scheduler(
        params['broker_url'],
        params['result_backend'],
        task_queue=params['broker_queue'])

    from beehive.module.scheduler.redis_scheduler import RedisScheduler

    beat = task_scheduler.Beat(loglevel=logging.getLevelName(internal_logger_level),
                               logfile='%s/%s.scheduler.log' % (log_path, params['api_id']),
                               pidfile='%s/%s.scheduler.pid' % (run_path, params['api_id']),
                               scheduler_cls=RedisScheduler)

    def terminate(*args):
        pass

    for sig in (SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT):
        signal(sig, terminate)

    beat.run()
