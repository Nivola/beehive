# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import requests
from logging import getLogger
from beehive.common.task_v2.manager import task_manager
from beehive.common.task_v2 import BaseTask, task_step
from beehive.module.catalog.controller import Catalog

logger = getLogger(__name__)


class RefreshCatalogTask(BaseTask):
    name = 'refresh_catalog_task'
    entity_class = Catalog

    """Refresh catalog task
    """
    def __init__(self, *args, **kwargs):
        super(RefreshCatalogTask, self).__init__(*args, **kwargs)

        self.steps = [
            RefreshCatalogTask.check_endpoints_step
        ]

    def get_endpoints(self, oid=None):
        """Get all endpoints
        """
        endpoints, tot = self.controller.get_endpoints(oid=oid)
        return endpoints

    def ping_endpoint(self, endpoint):
        """Ping endpoint

        :param endpoint: CatalogEndpoint instance
        """
        uri = endpoint.model.uri
        url = u'%s/v1.0/server/ping' % endpoint.model.uri

        res = False
        try:
            # issue a get request
            http = requests.get(url, timeout=(5, 5))

            if http.status_code == 200:
                res = True
            http.close()
        except Exception as ex:
            logger.error(ex, exc_info=1)

        logger.debug('Ping endpoint %s: %s' % (uri, res))
        return res

    def remove_endpoint(self, endpoint):
        """Remove endpoint

        :param endpoint: CatalogEndpoint instance
        """
        res = endpoint.delete()
        logger.debug('Delete endpoint: %s' % endpoint.uuid)
        return res

    @staticmethod
    @task_step()
    def check_endpoints_step(task, step_id, params, *args, **kvargs):
        """Check endpoints step

        :param task: parent celery task
        :param dict params: step params
        :param str step_id: step id
        """
        endpoints = task.get_endpoints()

        for endpoint in endpoints:
            RefreshCatalogTask.check_endpoint_step(task, step_id, params, endpoint)

    @staticmethod
    @task_step()
    def check_endpoint_step(task, step_id, params, endpoint, *args, **kvargs):
        """Check endpoint step

        :param task: parent celery task
        :param dict params: step params
        :param str step_id: step id
        :param str endpoint: endpoint instance
        """
        ping = task.ping_endpoint(endpoint)
        task.progress(step_id, msg='ping endpoint %s' % endpoint.name)
        if ping is False:
            task.remove_endpoint(endpoint)
            task.progress(step_id, msg='remove endpoint %s' % endpoint.name)
        return ping


task_manager.tasks.register(RefreshCatalogTask())
