#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

"""
Usage: scheduler.py config_file
  
Options:
  -h, --help               Print help and exit
  -v, --version            Print version and exit
  -c, --command=CMD        Command: start, stop, reload, trace
                           Require args = service name
"""
import sys, os
from collections import OrderedDict

if __name__ == '__main__':
    virtualenv = sys.argv[1:][0]
    config_file = sys.argv[1:][1]

    activate_this = '%s/bin/activate_this.py' % virtualenv
    execfile(activate_this, dict(__file__=activate_this))

    from six.moves.configparser import RawConfigParser

    # from http://stackoverflow.com/questions/15848674/how-to-configparse-a-file-keeping-multiple-values-for-identical-keys
    # How to ConfigParse a file keeping multiple values for identical keys
    #
    class MultiOrderedDict(OrderedDict):
        def __setitem__(self, key, value):
            if isinstance(value, list) and key in self:
                self[key].extend(value)
            else:
                super(MultiOrderedDict, self).__setitem__(key, value)

    config = RawConfigParser(dict_type=MultiOrderedDict)
    config.read(config_file)

    params = {i[0]:i[1] for i in config.items('uwsgi')}
    params['task_module'] = params['task_module'].split('\n')
    params['api_module'] = params['api_module'].split('\n')
    if 'api_plugin' in params:
        params['api_plugin'] = params['api_plugin'].split('\n')

    import beecell.server.gevent_ssl
    from gevent import monkey; monkey.patch_all()
    from beehive.common.task.manager import start_scheduler

    start_scheduler(params)