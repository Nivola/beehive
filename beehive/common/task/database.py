# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.task import BaseTask
from beehive.common.data import operation


class DatabaseTask(BaseTask):
    abstract = True

    def __init__(self, *args, **kwargs):
        BaseTask.__init__(self, *args, **kwargs)

    def _get_session(self):
        self.app.api_manager.get_session()

    def _flush_session(self):
        self.app.api_manager.flush_session()

    def _release_session(self):
        self.app.api_manager.release_session()

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Handler called after the task returns.

        Parameters:

            status - Current task state.
            retval - Task return value/exception.
            task_id - Unique id of the task.
            args - Original arguments for the task that returned.
            kwargs - Original keyword arguments for the task that returned.
            einfo - ExceptionInfo instance, containing the traceback (if any).

        The return value of this handler is ignored.
        """
        BaseTask.after_return(self, status, retval, task_id, args, kwargs, einfo)

        if operation.session is not None:
            self._release_session()
