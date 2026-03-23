# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from __future__ import annotations
import logging
from typing import Union, TYPE_CHECKING
from celery.canvas import Signature as CelerySignature
from celery.utils import abstract
if TYPE_CHECKING:
    from celery.app import Celery

logger = logging.getLogger("beehive.common")


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
        logger.debug("args - {0}".format(args))

        # kwargs.update({
        #     "timeout": 27
        # })
        logger.debug("kwargs: %s" % kwargs)
        logger.debug("route_name: %s" % route_name)

        # options.update({
        #     "timeout": 28
        # })
        logger.debug("**options: %s" % options)

        taskid = CelerySignature.apply_async(
            self,
            args,
            kwargs,
            route_name,
            retry=True,
            # parameters supported by the retry_over_time() function
            retry_policy={
                "interval_start": 0, # First retry immediately,
                "interval_step": 3,  # then increase by 2s for every retry.
                "interval_max": 31,  # but don't exceed 30s between retries.
                "max_retries": 98,   # give up after 30 tries.
                # File "/usr/local/lib/python3.9/site-packages/kombu/messaging.py", line 185, in publish |||
                # _publish = self.connection.ensure(self, _publish, **retry_policy) |||
                # TypeError: ensure() got an unexpected keyword argument 'timeout'
                # "timeout": 26,
            },
            timeout=26,
            **options,
        )
        logger.debug("Create new task: %s" % taskid)
        return taskid


def signature(varies, *args, **kwargs) -> Union[Signature, CelerySignature, abstract.CallableSignature]:
    """Create new signature.

    - if the first argument is a signature already then it's cloned.
    - if the first argument is a dict, then a Signature version is returned.

    :return: Signature: The resulting signature.
    """
    logger.debug("signature - args - {0}".format(args))
    logger.debug("signature - kwargs: %s" % kwargs)
    logger.debug("signature - varies: %s" % varies)

    app: 'Celery' = kwargs.get("app")
    if isinstance(varies, dict):
        if isinstance(varies, abstract.CallableSignature):
            return varies.clone()
        return Signature.from_dict(varies, app=app)
    return Signature(varies, *args, **kwargs)
