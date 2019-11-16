# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import sys
import os

sys.path.append("..")
sys.path.append(os.path.expanduser("~/workspace/git/gibboncloudapi"))
sys.path.append(os.path.expanduser("~/workspace/git/beecell"))
sys.path.append(os.path.expanduser("~/workspace/git/beedrones"))
syspath = os.path.expanduser("~")

# start event consumer
from gibboncloudapi.module.event.manager import start_event_consumer

params = {'api_id':'server-01',
          'api_name':'beehive',
          'api_subsystem':'event',
          'api_package':'beehive',
          'api_env':'beehive100',
          'database_uri':'mysql+pymysql://event:event@10.102.184.57:3306/event',
          'api_module':['gibboncloudapi.module.event.mod.EventModule'],
          'api_plugin':[]}
start_event_consumer(params, log_path='/tmp')