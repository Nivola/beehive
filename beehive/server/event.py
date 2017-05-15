#!/usr/bin/env python

'''
Created on Oct 13, 2014

@author: darkbk

Usage: event.py config_file
  
Options:
  -h, --help               Print help and exit
  -v, --version            Print version and exit
  -c, --command=CMD        Command: start, stop, reload, trace
                           Require args = service name
'''
import sys, os
import ConfigParser
from collections import OrderedDict

if __name__ == u'__main__':
    virtualenv = sys.argv[1:][0]
    config_file = sys.argv[1:][1]

    # from http://stackoverflow.com/questions/15848674/how-to-configparse-a-file-keeping-multiple-values-for-identical-keys
    # How to ConfigParse a file keeping multiple values for identical keys
    #
    class MultiOrderedDict(OrderedDict):
        def __setitem__(self, key, value):
            if isinstance(value, list) and key in self:
                self[key].extend(value)
            else:
                super(MultiOrderedDict, self).__setitem__(key, value)

    config = ConfigParser.RawConfigParser(dict_type=MultiOrderedDict)
    config.read(config_file)

    params = {i[0]:i[1] for i in config.items(u'uwsgi')}
    #params['task_module'] = params['task_module'].split('\n')
    params[u'api_module'] = params[u'api_module'].split(u'\n')
    #params['api_plugin'] = params['api_plugin'].split('\n')

    activate_this = u'%s/bin/activate_this.py' % virtualenv
    execfile(activate_this, dict(__file__=activate_this))

    import beecell.server.gevent_ssl
    from gevent import monkey; monkey.patch_all()
    from beehive.module.event.manager import start_event_consumer
    start_event_consumer(params)