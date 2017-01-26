'''
Created on Jan 25, 2017

@author: darkbk
'''
import sys
import os

sys.path.append("..")
sys.path.append(os.path.expanduser("~/workspace/git/gibboncloudapi"))
sys.path.append(os.path.expanduser("~/workspace/git/beecell"))
sys.path.append(os.path.expanduser("~/workspace/git/beedrones"))
syspath = os.path.expanduser("~")

# start event consumer
from gibboncloudapi.module.event.manager import start_event_consumer

params = {u'api_id':u'server-01',
          u'api_name':u'beehive',
          u'api_subsystem':u'event',
          u'api_package':u'beehive',
          u'api_env':u'beehive100',
          u'database_uri':u'mysql+pymysql://event:event@10.102.184.57:3306/event',
          u'api_module':[u'gibboncloudapi.module.event.mod.EventModule'],
          u'api_plugin':[]}
start_event_consumer(params, log_path=u'/tmp')