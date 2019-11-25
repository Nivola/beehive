# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import ujson as json
import logging
from beehive.common.data import query
from beehive.common.model import AbstractDbManager, PaginatedQueryGenerator, SchedulerTask
from beecell.db import ModelError


logger = logging.getLogger(__name__)


class SchedulerDbManager(AbstractDbManager):
    """
    """
    @query
    def get_tasks(self):
        """Get tasks.

        :raise QueryError: if query return error
        """
        session = self.get_session()
        query = session.query(distinct(DbEvent.type)).all()
        res = [i[0] for i in query]

        if len(res) == 0:
            self.logger.error('No event types found')
            raise SQLAlchemyError('No event types found')

        self.logger.debug('Get event types: %s' % truncate(res))

        return res

    @query
    def get_entity_definitions(self):
        """Get event entity definition.

        :raise QueryError: if query return error
        """
        session = self.get_session()
        query = session.query(distinct(DbEvent.objdef)).all()
        res = [i[0].lower() for i in query]

        if len(res) == 0:
            self.logger.error('No entity definitions found')
            raise SQLAlchemyError('No entity definitions found')

        self.logger.debug('Get entity definitions: %s' % truncate(res))

        return res

    def get_task(self, oid):
        """Get task

        :param oid: can be db id or event_id
        :return: DbEvent instance
        """
        session = self.get_session()

        # get obj by uuid
        if match('[0-9a-z]+', b(oid)):
            query = session.query(DbEvent).filter_by(event_id=oid)
        # get obj by id
        elif match('[0-9]+', b(oid)):
            query = session.query(DbEvent).filter_by(id=oid)

        entity = query.first()

        if entity is None:
            msg = 'No event found'
            self.logger.error(msg)
            raise ModelError(msg, code=404)

        self.logger.debug('Get event: %s' % (truncate(entity)))
        return entity

    @query
    def get_tasks(self, tags=[], page=0, size=10, order='DESC', field='id', with_perm_tag=None, *args, **kvargs):
        """Get tasks with some permission tags


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
        # query.add_relative_filter('AND t3.type = :type', 'type', kvargs)
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

    def delete(self, ):
        """Delete events"""
