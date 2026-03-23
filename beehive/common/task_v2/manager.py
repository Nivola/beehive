# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

import logging
import os
from beecell.util import ensure_text
from beecell.logger.helper import LoggerHelper
from signal import SIGHUP, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGQUIT
from signal import signal
from datetime import timedelta
from celery.utils.term import colored
from celery.utils.log import ColorFormatter
from celery import Celery
from celery._state import get_current_task
from celery.signals import setup_logging, worker_ready, task_received
from kombu import Exchange, Queue
from celery import __version__ as celeryVers

from beecell.logger.k8s_handler import K8shHandler
from beehive.common.apimanager import ApiManager
from beehive.common.data import operation

logger = logging.getLogger(__name__)


class ExtTaskFormatter(ColorFormatter):
    def format(self, record):
        record.__dict__.update(task_id="xxx", task_name="xxx")
        if hasattr(record, "update_task_info") and callable(getattr(record, "update_task_info")):
            # only for task_manager logs, but not for task_scheduler logs
            record.update_task_info()
        return logging.Formatter.format(self, record)

internal_logger_level = LoggerHelper.DEBUG

##################
def _configure_server_v3(config_file):
    # in teoria andrebbe altrove, prima di qualsiasi cosa
    from gevent import monkey
    monkey.patch_all()
    #
    import yaml

    f = open(config_file, "r")
    data = f.read()
    for k, v in dict(os.environ).items():
        data = data.replace("$(%s)" % k, v)

    data = data.replace("%d", "")
    params = yaml.safe_load(data)
    params = params.get("uwsgi")
    f.close()

    fields = ["task_module", "event_handler"]
    for field in fields:
        num = int(params.pop(field, 0))
        if num > 0:
            num += 1
            params[field] = []
            for i in range(1, num):
                item = params.pop("%s.%s" % (field, i))
                params[field].append(item)

    return params

def __getattr__(name):
    """
    da rimuovere. consente di fare
    from beehive.common.task... import task_manager
    e di avere direttamente il singleton.
    meglio sanare gli eventuali utilizzi rimanenti e rimuovere.
    """
    if name == "task_manager":
        return get_task_manager()
    elif name == "task_scheduler":
        return get_task_scheduler()

from threading import Lock
_lazy_cache = {}
_lazy_lock = Lock()
def get_task_manager() -> Celery:
    with _lazy_lock:
        if "task_manager" not in _lazy_cache:
            # read configuration
            params = _configure_server_v3("/etc/uwsgi/uwsgi.yaml")
            has_task_module = params.get("task_module")

            if has_task_module:
                logger.debug(f"[TASK_MANAGER] get_task_manager called from {__file__}, module id: {id(__name__)}")
                _task_manager_instance = Celery("tasks")
                logger.info(f"[TASK_MANAGER] creating task_manager at {id(_task_manager_instance)}: {_task_manager_instance}")

                # Configure the task manager
                configure_task_manager(_task_manager_instance,
                    #api_manager=api_manager,
                    broker_url=params["broker_url"],
                    result_backend=params["result_backend"],
                    tasks=params["task_module"],
                    task_queue=params["broker_queue"],
                    time_limit=params["task_time_limit"]
                )
            else:
                _task_manager_instance = None
            _lazy_cache["task_manager"] = _task_manager_instance
    return _lazy_cache["task_manager"]

def get_task_scheduler() -> Celery:
    with _lazy_lock:
        if "task_scheduler" not in _lazy_cache:
            logger.debug(f"[TASK_SCHEDULER] get_task_scheduler called from {__file__}, module id: {id(__name__)}")
            _task_scheduler_instance = Celery("scheduler")
            logger.info(f"[TASK_SCHEDULER] creating task_scheduler at {id(_task_scheduler_instance)}: {_task_scheduler_instance}")

            # read configuration
            params = _configure_server_v3("/etc/uwsgi/uwsgi.yaml")
            configure_task_scheduler(
                _task_scheduler_instance,
                schedule_backend=params["result_backend"],
                broker_url=params["broker_url"],
                task_queue=params["broker_queue"],
            )
            _lazy_cache["task_scheduler"] = _task_scheduler_instance

    return _lazy_cache["task_scheduler"]

@task_received.connect
def debug_task_received(sender=None, request=None, **kwargs):
    logger.debug("=== TASK RECEIVED DEBUG ===")
    logger.debug(f"Task class / sender: {sender}")
    logger.debug(f"Request name: {request.name}")
    logger.debug(f"Request ID: {request.id}")
    logger.debug(f"Request args: {request.args}")
    logger.debug(f"Request kwargs: {request.kwargs}")
    logger.debug("===========================")

# setup logging
@setup_logging.connect
def on_celery_setup_logging(**args):
    pass


@worker_ready.connect
def on_celery_worker_ready(**args):
    logger.info("########## WORKER STARTED ##########")
    app = get_task_manager()
    logger.info("App: %s - Worker knows the following tasks:" % app)
    for name in sorted(app.tasks.keys()):
        logger.info("- %s", name)

def configure_task_manager(
    task_manager_instance: 'Celery',
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
    task_manager_instance.conf.update(
        broker_url=ensure_text(broker_url),
        broker_pool_limit=10, # vedi default
        broker_connection_timeout=20, # default 4 sec
        # broker_heartbeat=20,
        broker_connection_max_retries=99,
        broker_transport_options={"max_retries": 99}, # max_retries default None
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
        task_time_limit=time_limit + 60, # Default: No time limit
        task_soft_time_limit=time_limit,
        worker_prefetch_multiplier=4, # default
        worker_concurrency=10, # If you tasks are CPU bound, then limit to the number of cores, otherwise increase substainally (50)
        # worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s:%(task_id)s] '
        #                        '%(name)s:%(funcName)s:%(lineno)d - %(message)s',
        worker_task_log_format="%(asctime)s %(levelname)s %(process)s:%(thread)s %(api_id)s "
        "%(task_name)s:%(task_id)s:%(step_name) %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        # worker_max_tasks_per_child=20
    )
    logger.debug("register tasks path: %s" % tasks)
    logger.debug("task_manager.conf: %s" % task_manager_instance.conf)
    #task_manager_instance.finalize()
    return


def configure_task_scheduler(
    task_scheduler_instance: 'Celery',
    broker_url,
    schedule_backend,
    task_queue=None
):
    """Configure task scheduler

    :param broker_url: url of the broker
    :param schedule_backend: url of the schedule backend where schedule entries are stored
    :param tasks: list of tasks module. Ex.
                  ['beehive.module.scheduler.tasks', 'beehive.module.service.plugins.filesharing',]
    """
    task_queue = ensure_text(task_queue)
    task_scheduler_instance.conf.update(
        task_default_queue=task_queue,
        broker_url=ensure_text(broker_url),
        broker_pool_limit=10, # vedi default
        broker_connection_timeout=21, # default 4 sec
        broker_connection_max_retries=95,
        broker_transport_options={"max_retries": 95}, # max_retries default None
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

    return


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

        def update_task_info(self):
            try:
                from celery import current_task
                task = current_task._get_current_object() if current_task else None
                #task = get_current_task()
                if task and getattr(task, 'request', None):
                    self.task_id = task.request.id
                    self.task_name = task.name.split(".")[-1]
                    self.step_id = task.current_step_id
                    self.step_name = task.current_step_name
            except Exception:
                # fallback if Celery isn't ready yet
                self.task_id = "xxx"
                self.task_name = "xxx"
                self.step_id = "xxx"
                self.step_name = "xxx"

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
    tmi = get_task_manager()

    api_manager = ApiManager(params, hostname=ensure_text(params.get("api_host")))
    api_manager.configure()
    #api_manager.register_modules(register_api=False, register_task=True)
    #task_manager.api_manager = api_manager
    tmi.api_manager = api_manager
    api_manager.task_manager = tmi
    api_manager.register_modules(register_api=False, register_task=True)

    argv = [
        "worker",  # from version 5.x
        "--hostname=" + ensure_text(params["broker_queue"]) + "@%h",
        "--loglevel=%s" % logging.getLevelName(internal_logger_level),
        "--purge",
        # '--logfile=%s' % file_name,
        # '--pool=prefork',
        "--pool=gevent",
        # '-O fair',
        # following params for workers
        # https://stackoverflow.com/questions/55249197/what-are-the-consequences-of-disabling-gossip-mingle-and-heartbeat-for-celery-w
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

    tmi.worker_main(argv)


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

    tsi = get_task_scheduler()
    api_manager = ApiManager(params)
    api_manager.configure()

    tsi.api_manager = api_manager
    api_manager.task_scheduler = tsi
    api_manager.register_modules()

    beat = tsi.Beat(
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
    tmi = get_task_manager()
    api_manager = ApiManager(params, hostname=ensure_text(params.get("api_host")))
    api_manager.configure()
    api_manager.register_modules(register_api=False)
    tmi.api_manager = api_manager
    api_manager.task_manager = tmi

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

    return True
