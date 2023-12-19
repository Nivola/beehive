# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

import logging
from celery.canvas import Signature as CelerySignature
from celery.utils import abstract

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
        logger.debug("kwargs: %s" % kwargs)
        logger.debug("route_name: %s" % route_name)
        logger.debug("**options: %s" % options)

        taskid = CelerySignature.apply_async(self, args, kwargs, route_name, **options)
        logger.debug("Create new task: %s" % taskid)
        return taskid


def signature(varies, *args, **kwargs):
    """Create new signature.

    - if the first argument is a signature already then it's cloned.
    - if the first argument is a dict, then a Signature version is returned.

    :return: Signature: The resulting signature.
    """
    logger.debug("args - {0}".format(args))
    logger.debug("kwargs: %s" % kwargs)
    logger.debug("varies: %s" % varies)

    app = kwargs.get("app")
    if isinstance(varies, dict):
        if isinstance(varies, abstract.CallableSignature):
            return varies.clone()
        return Signature.from_dict(varies, app=app)
    return Signature(varies, *args, **kwargs)
