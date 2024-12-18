# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

import logging
from operator import mod
from uuid import uuid4
from beehive.common.apimanager import ApiManagerError, ApiModule, ApiMethod
import ujson as json
import datetime
from beehive.common.data import operation
from beecell.simple import import_class, get_value

# from beehive.module.auth.controller import Objects, Role, User, Group
# from beehive.module.catalog.controller import Catalog, CatalogEndpoint
from beehive.common.model.config import ConfigDbManager
from beecell.db.manager import RedisManager
from beecell.db import QueryError


class BeehiveHelper(object):
    """Beehive subsystem manager helper."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__module__ + "." + self.__class__.__name__)

        from beehive.module.auth.controller import Objects, Role, User, Group
        from beehive.module.catalog.controller import Catalog, CatalogEndpoint

        self.classes = [Objects, Role, User, Group, Catalog, CatalogEndpoint]

    def get_permission_id(self, objdef):
        """Get operation objid

        :param objdef: objecy definition
        """
        temp = objdef.split(".")
        ids = ["*" for i in temp]
        return "//".join(ids)

    def set_permissions(self, classes=[]):
        """Set user operations

        :param classes: list of classes to include in perms
        """
        try:
            operation.perms = []
            for op in classes:
                perm = (
                    1,
                    1,
                    op.objtype,
                    op.objdef,
                    self.get_permission_id(op.objdef),
                    1,
                    "*",
                )
                operation.perms.append(perm)
        except Exception as ex:
            raise Exception("Permissions assign error: %s" % ex)

    def __configure(self, config, update=True):
        """Main configuration steps

        :param config: subsystem configuration
        :param update: if update is True don't replace database schema
        :return:
        """
        from beehive.common.apimanager import ApiManager

        msgs = []
        manager = None
        try:
            # create api manager
            params = {
                "api_id": "server-01",
                "api_name": config["api_system"],
                "api_subsystem": config["api_subsystem"],
                "api_env": "local",
                "api_prefix": config["api_prefix"],
                "database_uri": config["db_uri"],
                "api_module": 1,
                "api_module.1": "beehive.module.process.mod.ConfigModule",
                "api_plugin": 0,
            }
            manager = ApiManager(params)

            # remove and create scchema
            if update is False:
                ConfigDbManager.remove_table(config["db_uri"])
            ConfigDbManager.create_table(config["db_uri"])
            self.logger.info("Create config DB %s" % "")
            msgs.append("Create config DB %s" % "")

            # create session
            operation.session = manager.get_session()

            # create config db manager
            db_manager = ConfigDbManager()

            # set configurations
            #
            # populate configs
            #
            for item in config["config"]:
                # check if config already exists
                value = item["value"]
                if isinstance(value, dict):
                    value = json.dumps(value)
                try:
                    res = db_manager.get(app=config["api_system"], group=item["group"], name=item["name"])
                    self.logger.warning(
                        "Configuration %s %s %s already exist" % (config["api_system"], item["group"], item["name"])
                    )
                    msgs.append(
                        "Configuration %s %s %s already exist" % (config["api_system"], item["group"], item["name"])
                    )
                except QueryError as ex:
                    res = db_manager.add(config["api_system"], item["group"], item["name"], value)
                    self.logger.info("Add configuration %s" % res)
                    msgs.append("Add configuration %s" % res)
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise
        finally:
            # release session
            if manager is not None:
                manager.release_session()

        return msgs

    def __register_api_as_objects(self, module: ApiModule):
        manager = module.api_manager
        subsystem = manager.app_subsytem

        try:
            self.logger.info(f"Init api object {subsystem }.{ApiMethod.objdef} - START")
            # add object type for api ApiMethod
            manager.api_client.add_object_types(subsystem, ApiMethod.objdef)
            # add object for All ApiMethod
            objs = "*"
            manager.api_client.add_object(subsystem, ApiMethod.objdef, objs, ApiMethod.objdesc)
            self.logger.info(f"Init api object {subsystem}.{ApiMethod.objdef} - STOP")
        except ApiManagerError as ex:
            self.logger.warning(ex.value)
        for api in module.apis:
            try:
                api.register_api(module, only_auth=True)
            except Exception as ex:
                self.logger.warning(ex)

    def __init_subsystem(self, config, update=True):
        """Init beehive subsystem

        :param config: subsystem configuration
        :param update: if update is True don't replace database schema
        :return: trace of execution
        """
        from beehive.common.apimanager import ApiManager

        msgs = []

        try:
            # create api manager
            params = {
                "api_id": "server-01",
                "api_name": config["api_system"],
                "api_subsystem": config["api_subsystem"],
                "api_env": "local",
                "api_prefix": config["api_prefix"],
                "database_uri": config["db_uri"],
                "api_module": config["api_module"],
                "api_plugin": config["api_plugin"],
                "api_endpoint": config["api_endpoint"],
                "api_catalog": config["api_catalog"],
                "api_user": config["api_user"],
                "api_user_password": config["api_user_password"],
            }
            for i in range(1, params["api_module"] + 1):
                params["api_module.%s" % i] = config["api_module.%s" % i]
            if config["api_plugin"] > 0:
                for i in range(1, params["api_plugin"] + 1):
                    params["api_plugin.%s" % i] = config["api_plugin.%s" % i]
            manager = ApiManager(params)
            manager.configure()
            manager.register_modules()

            # create config db manager
            config_db_manager = ConfigDbManager()

            for db_manager_class in config["db_managers"]:
                db_manager = import_class(db_manager_class)

                # remove and create/update scchema
                if update is False:
                    db_manager.remove_table(config["db_uri"])
                db_manager.create_table(config["db_uri"])
                self.logger.info("Create DB %s" % db_manager_class)
                msgs.append("Create DB %s" % db_manager_class)
        except Exception as ex:
            self.logger.error(ex, exc_info=True)
            raise

        self.set_permissions(classes=self.classes)

        # create module
        for i in range(1, config["api_module"] + 1):
            item = config["api_module.%s" % i]
            try:
                self.logger.info("Load module %s" % item)
                module: ApiModule = manager.modules[item.split(".")[-1]]
                controller = module.get_controller()

                # create session
                operation.session = manager.get_session()

                # init module ###
                module.init_object()
                self.logger.info("Init module %s" % module)
                msgs.append("Init module %s" % module)

                # create system users and roles
                if module.name == "AuthModule":
                    res = self.__create_main_users(controller, config, config_db_manager, update)
                    controller.set_superadmin_permissions()
                    msgs.extend(res)

                elif module.name == "Oauth2Module":
                    controller.set_superadmin_permissions()

                elif module.name == "BasicModule":
                    controller.set_superadmin_permissions()

                elif module.name == "CatalogModule":
                    res = self.__create_main_catalogs(controller, config, config_db_manager)
                    controller.set_superadmin_permissions()
                    msgs.extend(res)

                elif module.name == "ServiceModule":
                    controller.populate(config["db_uri"])
                    msgs.extend("Populate service database")
                    self.__register_api_as_objects(module)

            except Exception as ex:
                self.logger.error(ex, exc_info=True)
                raise
            finally:
                # release session
                module.release_session()

        self.logger.info("Init subsystem %s" % (config["api_subsystem"]))
        msgs.append("Init subsystem %s" % (config["api_subsystem"]))

        return msgs

    def __create_main_users(self, controller, config, config_db_manager, update):
        """Create auth subsystem main users

        :param controller: catalog controller instance
        :param config: config
        :param config_db_manager: config db manager instance
        :param update: if update is True don't replace database schema
        :return:
        """
        msgs = []

        users = config["users"]

        if update is False:
            # add superadmin role
            # perms_to_assign = controller.get_superadmin_permissions()
            perms_to_assign = []
            controller.add_superadmin_role(perms_to_assign)

            # add guest role
            controller.add_guest_role()

        for user in users:
            # check if user already exist
            try:
                user = controller.get_user(user["name"])
                self.logger.warning("User %s already exist" % (user))
                msgs.append("User %s already exist" % (user))
            except Exception:
                # create superadmin
                if user["type"] == "admin":
                    expiry_date = datetime.datetime(2099, 12, 31)
                    user_id = controller.add_user(
                        name=user["name"],
                        storetype="DBUSER",
                        active=True,
                        password=user["pwd"],
                        desc=user["desc"],
                        expiry_date=expiry_date,
                        base=False,
                        system=True,
                    )

                # create users
                elif user["type"] == "user":
                    expiry_date = datetime.datetime(2099, 12, 31)
                    user_id = controller.add_user(
                        name=user["name"],
                        storetype="DBUSER",
                        active=True,
                        password=user["pwd"],
                        desc=user["desc"],
                        expiry_date=expiry_date,
                        base=True,
                        system=False,
                    )

                # add attribs to user
                attribs = user.get("attribs", [])
                user_obj = controller.get_user(user["name"])
                for a in attribs:
                    user_obj.set_attribute(name=a["name"], value=a["value"], desc=a["desc"])

                self.logger.info("Add user %s" % (user["name"]))
                msgs.append("Add user %s" % (user["name"]))

        return msgs

    def __create_main_catalogs(self, controller, config, config_db_manager):
        """Create auth/catalog subsystem main catalog

        :param controller: catalog controller instance
        :param config: config
        :param config_db_manager: config db manager instance
        :return:
        """
        msgs = []

        catalogs = config["catalogs"]

        for catalog in catalogs:
            # check if catalog already exist
            try:
                controller.get_catalog(catalog["name"])
                self.logger.warning("Catalog %s already exist" % (catalog["name"]))
                msgs.append("Catalog %s already exist" % (catalog["name"]))
            except Exception:
                # create new catalog
                cat = controller.add_catalog(catalog["name"], catalog["desc"], catalog["zone"])
                self.logger.info("Add catalog name:%s zone:%s : %s" % (catalog["name"], catalog["zone"], cat))
                msgs.append("Add catalog name:%s zone:%s : %s" % (catalog["name"], catalog["zone"], cat))

                # set catalog in config if internal
                if catalog["zone"] == "internal":
                    config_db_manager.add(config["api_system"], "api", "catalog", catalog["name"])

            # add endpoint
            for endpoint in catalog.get("endpoints", []):
                # check if endpoint already exist
                try:
                    controller.get_endpoint(endpoint["name"])
                    self.logger.warning("Endpoint %s already exist" % (endpoint["name"]))
                    msgs.append("Endpoint %s already exist" % (endpoint["name"]))
                except Exception:
                    # create new endpoint
                    cat = controller.get_catalog(catalog["name"])
                    res = cat.add_endpoint(
                        name=endpoint["name"],
                        desc=endpoint["desc"],
                        service=endpoint["service"],
                        uri=endpoint["uri"],
                        active=True,
                    )
                    self.logger.info(
                        "Add endpoint name:%s service:%s : %s" % (endpoint["name"], endpoint["service"], res)
                    )
                    msgs.append("Add endpoint name:%s service:%s : %s" % (endpoint["name"], endpoint["service"], res))

        return msgs

    def __setup_kombu_queue(self, config):
        """Setup kombu redis key fro queue

        :param config: queue config
        """
        configs = config["config"]
        for item in configs:
            if item["group"] == "queue":
                value = item["value"]
                queue = value["queue"]
                uri = value["uri"]
                manager = RedisManager(uri)
                manager.server.set("_kombu.binding.%s" % queue, value)

    def create_subsystem(self, subsystem_config, update=False):
        """Create subsystem.

        :param subsystem_config: subsystem configuration file
        :param update: if update is True don't replace database schema [default=False]
        """
        res = []

        # read subsystem config
        # config = read_file(subsystem_config)
        config = subsystem_config
        subsystem = get_value(config, "api_subsystem", None, exception=True)
        api_config = get_value(config, "api", {})

        if update is True:
            self.logger.info("Update %s subsystem" % subsystem)
        else:
            self.logger.info("Create new %s subsystem" % subsystem)

        # set operation user
        operation.user = (api_config.get("user", None), "localhost", None)
        operation.id = str(uuid4())
        self.set_permissions(classes=self.classes)

        # init auth subsytem
        if subsystem == "auth":
            res.extend(self.__configure(config, update=update))
            res.extend(self.__init_subsystem(config, update=update))

            # setup main kombu queue

        # init oauth2 subsytem
        elif subsystem == "oauth2":
            res.extend(self.__init_subsystem(config, update=update))

        # init other subsystem
        else:
            # create api client instance
            # client = BeehiveApiClient([config['api_endpoint']],
            #                           'keyauth',
            #                           api_config['user'],
            #                           api_config['pwd'],
            #                           None,
            #                           config['api_catalog'],
            #                           prefixuri=config['api_prefix'])

            # if update is False:
            #     # create super user
            #     user = {'name': '%s_admin@local' % config['api_subsystem'],
            #             'pwd': random_password(20),
            #             'desc': '%s internal user' % subsystem}
            #     try:
            #         client.add_system_user(user['name'], password=user['pwd'], desc='User %s' % user['name'])
            #     except BeehiveApiClientError as ex:
            #         if ex.code == 409:
            #             client.update_user(user['name'], user['name'], user['pwd'], 'User %s' % user['name'])
            #         else:
            #             raise
            #
            #     # append system user config
            #     config['config'].append({'group': 'api',
            #                              'name': 'user',
            #                              'value': {'name': user['name'], 'pwd': user['pwd']}})

            res.extend(self.__configure(config, update=update))
            res.extend(self.__init_subsystem(config, update=update))

        return res
