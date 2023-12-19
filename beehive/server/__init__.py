# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from sys import argv
import yaml
from beecell.types import is_string
import os


def configure_server():
    config_file = argv[1]
    f = open(config_file, "r")
    data = f.read()

    # replace key from environment
    # keys = ['API_FERNET_KEY', 'API_POD_IP', 'API_CATALOG', 'API_ENDPOINT', 'API_TIMEOUT', 'API_LOG',
    #         'PYTHONBASEPATH', 'LOGGING_LEVEL', 'GEVENT_NUMBER', 'OAUTH2_ENDPOINT', 'MYSQL_URI', 'REDIS_URI',
    #         'REDIS_QUEUE_URI', 'ELASTIC_NODES', 'TASK_EXPIRE', 'TASK_TIME_LIMIT', 'API_CLUSTER_IP', 'API_ENV',
    #         'API_PREFIX', 'API_OAUTH2_CLIENT']
    # for key in keys:
    #     val = os.getenv(key, '')
    #     data = data.replace('$(%s)' % key, val)

    for k, v in dict(os.environ).items():
        data = data.replace("$(%s)" % k, v)

    data = data.replace("%d", "")
    params = yaml.full_load(data)
    params = params.get("uwsgi")
    f.close()

    fields = ["task_module", "event_handler"]
    for field in fields:
        num = int(params.pop(field, 0))
        if num > 0:
            num += 1
            params[field] = []
            for i in range(1, num):
                item = params.pop("%s.%s" % (field, i))
                params[field].append(item)

    res = {}
    for k, v in params.items():
        if is_string(v):
            res[k] = v.encode("utf-8")
        else:
            res[k] = v

    from gevent import monkey

    monkey.patch_all()

    return res
