import logging
from celery.canvas import Signature as CelerySignature
from celery.utils import abstract
from beehive.common.task.handler import TaskResult

logger = logging.getLogger(u'beehive.common')


class Signature(CelerySignature):
    def apply_async1(self, args=(), kwargs={}, route_name=None, **options):
        """Apply this task asynchronously.

        Arguments:
            args (Tuple): Partial args to be prepended to the existing args.
            kwargs (Dict): Partial kwargs to be merged with existing kwargs.
            options (Dict): Partial options to be merged
                with existing options.

        Returns:
            ~@AsyncResult: promise of future evaluation.

        See also:
            :meth:`~@Task.apply_async` and the :ref:`guide-calling` guide.
        """
        #from beehive.common.task.handler import TaskResult
        #TaskResult.task_pending(args)
        jobid = CelerySignature.apply_async(self, args, kwargs, route_name, **options)
        task = TaskResult.task_pending(str(jobid))
        logger.warn(u'Create new task: %s' % task)
        return jobid


def signature(varies, *args, **kwargs):
    """Create new signature.

    - if the first argument is a signature already then it's cloned.
    - if the first argument is a dict, then a Signature version is returned.

    Returns:
        Signature: The resulting signature.
    """
    # return None
    app = kwargs.get('app')
    if isinstance(varies, dict):
        if isinstance(varies, abstract.CallableSignature):
            return varies.clone()
        return Signature.from_dict(varies, app=app)
    return Signature(varies, *args, **kwargs)


# celery.canvas.Signature = Signature