# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from beecell.simple import truncate
from beecell.server.uwsgi_server.resource import UwsgiManager, UwsgiManagerError
from beehive.common.apimanager import ApiManagerError, ApiViewResponse
from beehive.common.model.config import ConfigDbManager
from beecell.db import TransactionError
from beehive.common.controller.authorization import BaseAuthController


class BasicController(BaseAuthController):
    """Basic Module controller.

    :param module: ApiModule instance
    """

    version = "v1.0"

    def __init__(self, module):
        BaseAuthController.__init__(self, module)

        self.resource = UwsgiManager()
        self.child_classes = [ApiViewResponse]

    #
    # server info
    #
    def ping(self):
        """Ping server

        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            res = {
                "name": self.module.api_manager.app_name,
                "id": self.module.api_manager.app_id,
                "hostname": self.module.api_manager.server_name,
                "uri": self.module.api_manager.app_uri,
            }
            self.logger.debug("Ping server: %s" % truncate(res))
            return res
        except Exception as ex:
            self.logger.error(ex)
            return False

    def info(self):
        """Server Info

        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            res = {
                "name": self.module.api_manager.app_name,
                "id": self.module.api_manager.app_id,
                "modules": {k: v.info() for k, v in self.module.api_manager.modules.items()},
            }
            self.logger.debug("Get server info: %s" % truncate(res))
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=8000)

    def processes(self):
        """Get server process tree

        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            res = self.resource.info()
            return res
        except UwsgiManagerError as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=8000)

    def workers(self):
        """Get server workers statistics

        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            res = self.resource.stats()
            return res
        except UwsgiManagerError as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=8000)

    def reload(self):
        """Reload server

        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        try:
            res = self.resource.reload()
            return res
        except UwsgiManagerError as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=8000)

    def get_configs(self, app="beehive"):
        """Get server configuration.

        :param app: app name [default=cloudapi]
        :return: Config instance list
        :rtype: Config
        :raises ApiManagerError: if query empty return error.
        """
        try:
            manager = ConfigDbManager()
            confs = manager.get(app=app)

            res = []
            for c in confs:
                res.append({"type": c.group, "name": c.name, "value": c.value})
            self.logger.debug("Get server configuration: %s" % truncate(res))
            return res
        except (TransactionError, Exception) as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex)

    def get_uwsgi_configs(self):
        """Get uwsgi configuration params. List all configurations saved in .ini
        configuration file of the uwsgi instance.

        :return: uwsgi configurations list
        :rtype: Config
        :raises ApiManagerError: if query empty return error.
        """
        try:
            confs = self.module.api_manager.params

            res = []
            for k, v in confs.items():
                res.append({"key": k, "value": v})
            self.logger.debug("Get uwsgi configuration: %s" % truncate(res))
            return res
        except (TransactionError, Exception) as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex)
