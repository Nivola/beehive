#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

"""
Usage: batch.py config_file entityclass task_class jsonparameter
  python pkgs/beehive/beehive/server/batch.py  /etc/uwsgi/uwsgi.yaml beehive_service.controller.ApiAccount beehive_service.task_v2.metrics.AcquireMetricTask '{ "objid":"*"
}'

"""
from gevent import monkey

monkey.patch_all()


# conf='/etc/uwsgi/uwsgi.yaml'
# entity_class_name='beehive_service.controller.ApiAccount'
# task_name='beehive_service.task_v2.metrics.acquire_metric_task'
# task_class_name='beehive_service.task_v2.metrics.AcquireMetricTask'
# params_string='{}'

from beecell.simple import import_class, id_gen
from beehive.common.data import set_operation_params
from beehive.server import configure_server
from beehive.common.apimanager import ApiManager
from beehive.common.task_v2.manager import task_manager, configure_batch_task_manager
from beehive.common.task_v2 import prepare_or_run_task
from six import ensure_text
import ujson
from beehive.server import configure_server
from uuid import uuid4

from sys import argv

if __name__ == "__main__":
    params = configure_server()

    conf = argv[1]  #'/etc/uwsgi/uwsgi.yaml'
    entity_class_name = argv[2]  #'beehive_service.controller.ApiAccount'
    # task_name = argv[3]  #'beehive_service.task_v2.metrics.acquire_metric_task'
    task_class_name = argv[3]  #'beehive_service.task_v2.metrics.AcquireMetricTask'
    params_string = argv[4]  #'{}'

    task_params = ujson.loads(params_string)
    task_params["sync"] = False
    task_params["parent_task"] = ""
    task_params["hostname"] = "localhost"
    task_params["user"] = "task_manager"
    task_params["server"] = "localhost"
    task_params["identity"] = ""
    task_params["api_id"] = "batch"
    # task_params['objid'] = id_gen()
    task_params["task_id"] = id_gen()

    configure_batch_task_manager(params)
    set_operation_params(
        {
            "user": ("task_manager", "localhost", ""),
            "authorize": False,
            "id": ensure_text(params["api_id"]) + ".batch",
            "cache": False,
        }
    )

    api_manager: ApiManager = task_manager.api_manager
    entity_class = import_class(entity_class_name)
    # instance_class = entity_class(api_manager.main_module.get_controller())

    task_class = import_class(task_class_name)
    task_instance = task_class()
    task_instance.entity_class = entity_class
    task_instance.app = task_manager
    task_instance.entity_class = entity_class

    task_instance.get_session()
    task_instance.request.kwargsreprid = ""
    task_instance.request.id = str(uuid4())
    task_instance.task_result.task_prerun(task=task_instance, task_id=task_instance.request.id)
    task_instance.run(task_params)
