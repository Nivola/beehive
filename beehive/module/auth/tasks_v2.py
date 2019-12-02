# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

from datetime import datetime
from logging import getLogger
from beehive.common.controller.authorization import User
from beehive.common.task_v2.manager import task_manager
from beehive.common.task_v2 import BaseTask, task_step

logger = getLogger(__name__)


class DisableExpiredUsersTask(BaseTask):
    name = 'disable_expired_users_task'
    entity_class = User

    """Disable expired users
    """
    def __init__(self, *args, **kwargs):
        super(DisableExpiredUsersTask, self).__init__(*args, **kwargs)

        self.steps = [
            DisableExpiredUsersTask.disable_expired_users_task_step
        ]

    @staticmethod
    @task_step()
    def disable_expired_users_task_step(task, step_id, params, *args, **kvargs):
        """Disable expired users

        :param task: parent celery task
        :param dict params: step params
        :param str step_id: step id
        """
        expiry_date = datetime.today()
        task.controller.auth_manager.expire_users(expiry_date)


class RemoveExpiredRolesFromUsersTask(BaseTask):
    name = 'remove_expired_roles_from_users_task'
    entity_class = User

    """Disable expired users
    """
    def __init__(self, *args, **kwargs):
        super(RemoveExpiredRolesFromUsersTask, self).__init__(*args, **kwargs)

        self.steps = [
            RemoveExpiredRolesFromUsersTask.remove_expired_roles_from_users_step
        ]

    @staticmethod
    @task_step()
    def remove_expired_roles_from_users_step(task, step_id, params, *args, **kvargs):
        """Remove expired roles from users

        :param task: parent celery task
        :param dict params: step params
        :param str step_id: step id
        """
        expiry_date = datetime.today()
        task.controller.auth_manager.remove_expired_user_role(expiry_date)


task_manager.tasks.register(DisableExpiredUsersTask())
task_manager.tasks.register(RemoveExpiredRolesFromUsersTask())
