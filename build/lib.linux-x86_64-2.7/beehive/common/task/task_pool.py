# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

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
from kombu import Exchange, Queue
from beehive.common.apimanager import ApiManager

from celery.concurrency.gevent import TaskPool as GeventTaskPool
from beehive.common.task.handler import TaskResult

logger = logging.getLogger(__name__)

__all__ = ['TaskPool']


class TaskPool(GeventTaskPool):
    """GEvent Pool."""

    def on_apply(self, target, args=None, kwargs=None, callback=None, accept_callback=None, timeout=None,
                 timeout_callback=None, **_):

        # TaskResult.task_pending(args)
        return GeventTaskPool.on_apply(self, target, args, kwargs, callback, accept_callback, timeout,
                                       timeout_callback, **_)
