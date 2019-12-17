# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

from sys import argv
import yaml
from beecell.simple import is_string


def configure_server():
    config_file = argv[1]

    f = open(config_file, 'r')
    data = f.read()
    data = data.replace('%d', '')
    params = yaml.full_load(data)
    f.close()

    params = params.get('uwsgi')

    fields = ['task_module', 'event_handler']
    for field in fields:
        num = int(params.pop(field, 0))
        if num > 0:
            params[field] = []
            for i in range(1, num):
                item = params.pop('%s.%s' % (field, i))
                params[field].append(item)

    res = {}
    for k, v in params.items():
        if is_string(v):
            res[k] = v.encode('utf-8')
        else:
            res[k] = v

    # import beecell.server.gevent_ssl
    from gevent import monkey
    monkey.patch_all()

    return res
