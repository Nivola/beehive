# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

import logging
import os
from six import ensure_text
from beecell.logger.helper import LoggerHelper
from signal import SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT
from signal import signal
from datetime import timedelta
from celery.utils.term import colored
from celery.utils.log import ColorFormatter
from celery import Celery
from celery._state import get_current_task
from celery.signals import setup_logging, worker_ready
from kombu import Exchange, Queue
from celery import __version__ as celeryVers

from beecell.logger.k8s_handler import K8shHandler
from beehive.common.apimanager import ApiManager
from beehive.common.data import operation

logger = logging.getLogger(__name__)


class ExtTaskFormatter(ColorFormatter):
    # COLORS = colored().names
    # colors = {
    #     'DEBUG': COLORS['blue'],
    #     'WARNING': COLORS['yellow'],
    #     'WARN': COLORS['yellow'],
    #     'ERROR': COLORS['red'],
    #     'CRITICAL': COLORS['magenta'],
    #     'DEBUG2': COLORS['green'],
    #     'DEBUG3': COLORS['cyan']
    # }

    def format(self, record):
        task = get_current_task()
        if task and task.request:
            name = task.name.split(".")[-1]
            record.__dict__.update(task_id=task.request.id, task_name=name)
        else:
            record.__dict__.update(task_id="xxx", task_name="xxx")
        return logging.Formatter.format(self, record)


internal_logger_level = LoggerHelper.DEBUG

task_manager = Celery("tasks")
task_scheduler = Celery("scheduler")


# setup logging
@setup_logging.connect
def on_celery_setup_logging(**args):
    pass


@worker_ready.connect
def on_celery_worker_ready(**args):
    logger.info("########## WORKER STARTED ##########")


def configure_task_manager(
    broker_url,
    result_backend,
    tasks=[],
    expire=60 * 60 * 24,
    task_queue="celery",
    time_limit=1200,
):
    """Configure Task manager

    :param broker_url: url of the broker
    :param result_backend: url of the result backend
    :param tasks: list of tasks module.
        Ex. ['beehive.module.scheduler.tasks', 'beehive.module.service.plugins.filesharing',]
    """
    # # get redis password
    # redis_password = None
    # if result_backend.find('@') > 0:
    #     redis_password = match(r"redis:\/\/([\w\W\d]*)@.", result_backend).groups()[0]
    task_queue = ensure_text(task_queue)
    task_manager.conf.update(
        broker_url=ensure_text(broker_url),
        broker_pool_limit=10,
        # broker_heartbeat=20,
        # broker_connection_max_retries=10,
        task_default_queue=task_queue,
        task_default_exchange=task_queue,
        task_default_routing_key=task_queue,
        task_queues=(Queue(task_queue, Exchange(task_queue), routing_key=task_queue),),
        result_backend=ensure_text(result_backend),
        task_ignore_result=True,
        result_expires=600,
        task_serializer="json",
        accept_content=["json"],  # Ignore other content
        result_serializer="json",
        timezone="Europe/Rome",
        enable_utc=True,
        imports=tasks,
        worker_disable_rate_limits=True,
        task_track_started=True,
        task_time_limit=time_limit + 60,
        task_soft_time_limit=time_limit,
        worker_concurrency=10,
        # worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s:%(task_id)s] '
        #                        '%(name)s:%(funcName)s:%(lineno)d - %(message)s',
        worker_task_log_format="%(asctime)s %(levelname)s %(process)s:%(thread)s %(api_id)s "
        "%(task_name)s:%(task_id)s:%(step_name) %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        # worker_max_tasks_per_child=20
    )
    logger.debug("register tasks path: %s" % tasks)

    return task_manager


def configure_task_scheduler(broker_url, schedule_backend, task_queue=None):
    """Configure task scheduler

    :param broker_url: url of the broker
    :param schedule_backend: url of the schedule backend where schedule entries are stored
    :param tasks: list of tasks module. Ex.
                  ['beehive.module.scheduler.tasks', 'beehive.module.service.plugins.filesharing',]
    """
    task_queue = ensure_text(task_queue)
    task_scheduler.conf.update(
        task_default_queue=task_queue,
        broker_url=ensure_text(broker_url),
        scheduler_backend=ensure_text(schedule_backend),
        scheduler_key_prefix=task_queue + ".schedule",
        task_serializer="json",
        accept_content=["json"],  # Ignore other content
        result_serializer="json",
        timezone="Europe/Rome",
        enable_utc=True,
        beat_max_loop_interval=5,
        # worker_prefetch_multiplier=1,
        beat_scheduler="beehive.module.scheduler_v2.redis_scheduler:RedisScheduler",
        beat_schedule={
            "test-every-30-minutes": {
                "task": "beehive.module.scheduler_v2.tasks.test",
                "schedule": timedelta(minutes=1),
                "args": ("*", {}),
                "options": {"queue": task_queue},
            },
        },
    )
    logger.debug("configured task scheduler: %s" % task_queue)

    return task_scheduler


def start_task_manager(params):
    """Start celery task manager

    :param params: configuration params
    """

    class BeehiveLogRecord(logging.LogRecord):
        def __init__(self, *args, **kwargs):
            super(BeehiveLogRecord, self).__init__(*args, **kwargs)

            self.api_id = getattr(operation, "id", "xxx")
            self.task_id = "xxx"
            self.task_name = "xxx"
            self.step_id = "xxx"
            self.step_name = "xxx"

            task = get_current_task()
            if task and task.request:
                self.task_id = task.request.id
                self.task_name = task.name.split(".")[-1]
                self.step_id = task.current_step_id
                self.step_name = task.current_step_name

    logging.setLogRecordFactory(BeehiveLogRecord)

    logger_level = int(os.getenv("LOGGING_LEVEL", logging.DEBUG))
    celery_logger = logging.getLogger("celery")
    main_loggers = [
        celery_logger,
        logging.getLogger("beehive"),
        # logging.getLogger('beehive.common.model'),
        logging.getLogger("beehive_service"),
        logging.getLogger("beehive_service_netaas"),
        logging.getLogger("beehive_resource"),
        logging.getLogger("beehive.db"),
        logging.getLogger("beecell"),
        logging.getLogger("beedrones"),
        logging.getLogger("proxmoxer"),
        logging.getLogger("requests"),
    ]
    frmt = (
        "%(asctime)s %(levelname)s %(process)s:%(thread)s %(api_id)s::%(task_name)s:%(task_id)s:%(step_name)s"
        " %(name)s:%(funcName)s:%(lineno)d | %(message)s"
    )
    LoggerHelper.simple_handler(
        main_loggers,
        logger_level,
        frmt=frmt,
        formatter=ExtTaskFormatter,
        handler=K8shHandler,
    )
    celery_logger.setLevel(logging.INFO)

    # setup api manager
    api_manager = ApiManager(params, hostname=ensure_text(params.get("api_host")))
    api_manager.configure()
    api_manager.register_modules(register_api=False, register_task=True)
    task_manager.api_manager = api_manager

    configure_task_manager(
        params["broker_url"],
        params["result_backend"],
        tasks=params["task_module"],
        expire=params["expire"],
        task_queue=params["broker_queue"],
        time_limit=params["task_time_limit"],
    )

    argv = [
        "worker",  # from version 5.x
        "--hostname=" + ensure_text(params["broker_queue"]) + "@%h",
        "--loglevel=%s" % logging.getLevelName(internal_logger_level),
        "--purge",
        # '--logfile=%s' % file_name,
        # '--pool=prefork',
        "--pool=gevent",
        # '-O fair',
        "--without-gossip",
        "--without-heartbeat",
        "--without-mingle",
        "--task-events",
        # '--pidfile=%s' % pid_name,
    ]

    logger.info("celeryVers: " + celeryVers)
    major = celeryVers.split(".")[0]
    if int(major) < 5:
        argv.pop(0)

    def terminate(*args):
        task_manager.stop()

    # for sig in (SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT):
    #    signal(sig, terminate)

    task_manager.worker_main(argv)


def start_scheduler(params):
    """start celery scheduler

    :param params: configuration params
    """
    name = ensure_text(params["api_id"]) + ".scheduler"
    log_path = run_path = params.get("api_log", None)

    if log_path is not None:
        log_path = run_path = ensure_text(log_path)
    if log_path is None:
        log_path = "/var/log/%s/%s/" % (params["api_package"], params["api_env"])
        run_path = "/var/run/%s/%s/" % (params["api_package"], params["api_env"])

    file_name = log_path + name + ".log"
    # pid_name = run_path + name + '.pid'

    logger_level = logging.INFO
    loggers = [
        logging.getLogger("beehive"),
        logging.getLogger("beecell"),
        logging.getLogger("beedrones"),
        logging.getLogger("celery"),
    ]
    frmt = "%(asctime)s %(levelname)s %(process)s:%(thread)s %(name)s:%(funcName)s:%(lineno)d | %(message)s"
    LoggerHelper.simple_handler(
        loggers,
        logger_level,
        frmt=frmt,
        formatter=ExtTaskFormatter,
        handler=K8shHandler,
    )

    api_manager = ApiManager(params)
    api_manager.configure()
    api_manager.register_modules()
    task_scheduler.api_manager = api_manager

    configure_task_scheduler(
        params["broker_url"],
        params["result_backend"],
        task_queue=params["broker_queue"],
    )
    beat = task_scheduler.Beat(
        loglevel=logging.getLevelName(internal_logger_level), logfile=file_name
    )  # , pidfile=pid_name)

    def terminate(*args):
        pass

    for sig in (SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT):
        signal(sig, terminate)

    beat.run()


def configure_batch_task_manager(params):
    """Start celery task manager

    :param params: configuration params
    """
    name = ensure_text(params["api_id"]) + ".batch"
    log_path = run_path = params.get("api_log", None)

    if log_path is not None:
        log_path = run_path = ensure_text(log_path)
    if log_path is None:
        log_path = "/var/log/%s/%s/" % (params["api_package"], params["api_env"])

    run_path = "/var/run/%s/%s/" % (params["api_package"], params["api_env"])

    file_name = log_path + name + ".log"
    pid_name = run_path + name + ".pid"

    frmt = (
        "[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s:%(task_id)s] %(name)s:%(funcName)s:%(lineno)d"
        " - %(message)s"
    )

    celery_logger = logging.getLogger("celery")
    logger_level = int(os.getenv("LOGGING_LEVEL", logging.DEBUG))
    main_loggers = [
        celery_logger,
        logging.getLogger("beehive"),
        # logging.getLogger('beehive.common.model'),
        logging.getLogger("beehive_service"),
        logging.getLogger("beehive_resource"),
        logging.getLogger("beehive.db"),
        logging.getLogger("beecell"),
        logging.getLogger("beedrones"),
        logging.getLogger("proxmoxer"),
        logging.getLogger("requests"),
    ]
    LoggerHelper.simple_handler(
        main_loggers,
        logger_level,
        frmt=frmt,
        formatter=ExtTaskFormatter,
        handler=K8shHandler,
    )

    # setup api manager
    api_manager = ApiManager(params, hostname=ensure_text(params.get("api_host")))
    api_manager.configure()
    api_manager.register_modules(register_api=False)
    task_manager.api_manager = api_manager

    # elk logger
    if api_manager.elasticsearch is not None:
        frmt = (
            '{"timestamp":"%(asctime)s", "levelname":"%(levelname)s", "task_name":"%(task_name)s", '
            '"task_id":"%(task_id)s", "module":"%(name)s", "func":"%(funcName)s", "lineno":"%(lineno)d",'
            '"message":"%(message)s"}'
        )
        tags = []
        # main_loggers.append(celery_logger)
        LoggerHelper.elastic_handler(
            main_loggers,
            logger_level,
            api_manager.elasticsearch,
            index="cmp-%s" % api_manager.app_env,
            frmt=frmt,
            tags=tags,
            server=api_manager.server_name,
            app=api_manager.app_id,
            component="task",
        )
        celery_logger.setLevel(logging.INFO)

    configure_task_manager(
        params["broker_url"],
        params["result_backend"],
        tasks=params["task_module"],
        expire=params["expire"],
        task_queue=params["broker_queue"],
        time_limit=params["task_time_limit"],
    )

    return True
