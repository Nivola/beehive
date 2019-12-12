#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

"""
Usage: task.py virtual_env_path config_file
  
Options:
  -h, --help               Print help and exit
  -v, --version            Print version and exit
  -c, --command=CMD        Command: start, stop, reload, trace
                           Require args = service name
"""
from sys import argv
from sys import version_info


if __name__ == '__main__':
    virtualenv = argv[1:][0]

    activate_this = '%s/bin/activate_this.py' % virtualenv
    if version_info.major == 2:
        execfile(activate_this, dict(__file__=activate_this))
    else:
        import runpy
        file_globals = runpy.run_path(activate_this)

    from beehive.server import configure_server
    params = configure_server()

    # from beehive.common.task_v2.manager import start_task_manager
    from beehive.common.task.manager import start_task_manager
    start_task_manager(params)
