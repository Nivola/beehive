#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

"""
Usage: event.py virtual_env_path config_file
  
Options:
  -h, --help               Print help and exit
  -v, --version            Print version and exit
  -c, --command=CMD        Command: start, stop, reload, trace
                           Require args = service name
"""
if __name__ == '__main__':
    from beehive.server import configure_server
    params = configure_server()

    from beehive.module.event.manager import start_event_consumer
    start_event_consumer(params)
