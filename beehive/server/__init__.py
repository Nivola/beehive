# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

from sys import argv
from collections import OrderedDict
import yaml


def configure_server():
    # config_file = argv[1:][1]
    config_file = argv[1]

    # from six.moves.configparser import RawConfigParser
    #
    # class MultiOrderedDict(OrderedDict):
    #     def __setitem__(self, key, value):
    #         if isinstance(value, list) and key in self:
    #             self[key].extend(value)
    #         else:
    #             super(MultiOrderedDict, self).__setitem__(key, value)
    #
    # config = RawConfigParser(dict_type=MultiOrderedDict)
    # config.read(config_file)

    # params = {i[0]: i[1] for i in config.items('uwsgi')}
    # params['task_module'] = params.get('task_module', '').split('\n')
    # params['api_module'] = params.get('api_module', '').split('\n')
    # params['api_plugin'] = params.get('api_plugin', '').split('\n')
    # params['event_handler'] = params.get('event_handler', '').split('\n')

    f = open(config_file, 'r')
    data = f.read()
    data = data.replace('%d', '')
    params = yaml.full_load(data)
    f.close()

    params = params.get('uwsgi')

    fields = ['api_module']
    for field in fields:
        num = int(params.pop(field, 0))
        if num > 0:
            params[field] = []
            for i in range(1, num):
                item = params.pop('%s.%s' % (field, i))
                params[field].append(item)

    # import beecell.server.gevent_ssl
    from gevent import monkey
    monkey.patch_all()

    return params
