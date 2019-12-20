# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

import ujson as json
import logging

from sqlalchemy import text, asc

from beecell.simple import truncate
from beehive.common.data import query
from beehive.common.model import AbstractDbManager, PaginatedQueryGenerator, SchedulerTask, SchedulerStep, \
    SchedulerTrace
from beecell.db import ModelError


logger = logging.getLogger(__name__)


class SchedulerDbManager(AbstractDbManager):
    """Scheduler db manager

    :param session: sqlalchemy session
    """
    def get_steps(self, task_id):
        """Get task steps

        :param task_id: task id
        :return: SchedulerStep instance list
        """
        session = self.get_session()

        query = session.query(SchedulerStep).filter_by(task_id=task_id).order_by(asc(SchedulerStep.start_time))
        steps = query.all()
        self.logger.debug('Get task %s steps: %s' % (task_id, truncate(steps)))
        return steps

    def get_trace(self, task_id):
        """Get task trace

        :param task_id: task id
        :return: SchedulerTrace instance list
        """
        session = self.get_session()

        query = session.query(SchedulerTrace).filter_by(task_id=task_id).order_by(asc(SchedulerTrace.date))
        steps = query.all()
        self.logger.debug('Get task %s trace: %s' % (task_id, truncate(steps)))
        return steps

    @query
    def get_tasks(self, tags=[], page=0, size=10, order='DESC', field='id', with_perm_tag=None, *args, **kvargs):
        """Get tasks with some permission tags

        :param task_id: task id
        :param tags: list of permission tags
        :param page: users list page to show [default=0]
        :param size: number of users to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :param args: custom params
        :param kvargs: custom params
        :param with_perm_tag: if False disable authorization
        :return: list of entityclass
        :raises QueryError: raise :class:`QueryError`
        """
        query = PaginatedQueryGenerator(SchedulerTask, self.get_session(), with_perm_tag=with_perm_tag)

        # set filters
        query.add_relative_filter('AND t3.uuid = :task_id', 'task_id', kvargs)
        # query.add_relative_filter('AND t3.objid like :objid', 'objid', kvargs)
        # query.add_relative_filter('AND t3.objtype like :objtype', 'objtype', kvargs)
        # query.add_relative_filter('AND t3.objdef like :objdef', 'objdef', kvargs)
        # query.add_relative_filter('AND t3.data like :data', 'data', kvargs)
        # query.add_relative_filter('AND t3.source like :source', 'source', kvargs)
        # query.add_relative_filter('AND t3.dest like :dest', 'dest', kvargs)
        # query.add_relative_filter('AND t3.creation >= :datefrom', 'datefrom', kvargs)
        # query.add_relative_filter('AND t3.creation <= :dateto', 'dateto', kvargs)

        query.set_pagination(page=page, size=size, order=order, field=field)
        res = query.run(tags, *args, **kvargs)
        return res

    def delete(self):
        """Delete events"""
        pass
