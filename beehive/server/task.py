#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

"""
Usage: task.py virtual_env_path config_file
  
Options:
  -h, --help               Print help and exit
  -v, --version            Print version and exit
  -c, --command=CMD        Command: start, stop, reload, trace
                           Require args = service name
"""
from beehive.server import configure_server

if __name__ == '__main__':
    params = configure_server()

    from beehive.common.task.manager import start_task_manager
    start_task_manager(params)
