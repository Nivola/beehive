# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import logging
from celery.canvas import Signature as CelerySignature
from celery.utils import abstract
from beehive.common.task_v2.handler import TaskResult

logger = logging.getLogger('beehive.common')


class Signature(CelerySignature):
    def apply_async(self, args=(), kwargs={}, route_name=None, **options):
        """Apply this task asynchronously.

        :param tuple args: Partial args to be prepended to the existing args.
        :param dict kwargs : Partial kwargs to be merged with existing kwargs.
        :param dict options: Partial options to be merged with existing options.

        :return: ~@AsyncResult: promise of future evaluation.

        See also:
            :meth:`~@Task.apply_async` and the :ref:`guide-calling` guide.
        """
        taskid = CelerySignature.apply_async(self, args, kwargs, route_name, **options)
        # task = TaskResult().task_pending(str(taskid))
        logger.debug('Create new task: %s' % taskid)
        return taskid


def signature(varies, *args, **kwargs):
    """Create new signature.

    - if the first argument is a signature already then it's cloned.
    - if the first argument is a dict, then a Signature version is returned.

    :return: Signature: The resulting signature.
    """
    app = kwargs.get('app')
    if isinstance(varies, dict):
        if isinstance(varies, abstract.CallableSignature):
            return varies.clone()
        return Signature.from_dict(varies, app=app)
    return Signature(varies, *args, **kwargs)
