'''
Created on Jan 30, 2015

@author: darkbk

TODO: make test like auth
'''
from tests.test_util import run_test, CloudapiTestCase
import ujson as json
import unittest
from beehive.util.auth import AuthClient
import random
import tests.test_util

uid = None
seckey = None
task_id = 'd124ef29-7c57-423e-b6d9-b72d519d7600'

class SchedulerAPITestCase(CloudapiTestCase):
    """To execute this test you need a cloudstack instance.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        
        self.auth_client = AuthClient()
        self.api_id = u'api'
        self.module = u'tenant'
        
    def tearDown(self):
        CloudapiTestCase.tearDown(self)
        
    #
    # task manager
    #
    def test_ping_task_manager(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/task/ping/'
        
        self.invoke(self.module, uri, u'GET', data=data)

    def test_stat_task_manager(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/task/stats/'
        
        res = self.invoke(self.module, uri, u'GET', data=data)
        self.logger.info(self.pp.pformat(res))

    def test_report_task_manager(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/task/report/'
        
        res = self.invoke(self.module, uri, u'GET', data=data)
        self.logger.info(self.pp.pformat(res))
    
    def test_get_all_tasks(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/task/tasks/'
        
        res = self.invoke(self.module, uri, u'GET', data=data)
        self.logger.info(self.pp.pformat(res))
        
    def test_get_task(self):
        global uid, seckey
                
        data = u''
        task_id = u'6d21c46a-d1bc-4435-9d26-5d75881f6cb1'
        uri = u'/v1.0/task/task/%s/' % task_id
        
        res = self.invoke(self.module, uri, u'GET', data=data)
        self.logger.info(self.pp.pformat(res))
        
    def test_get_task_graph(self):
        global uid, seckey, task_id
        data = u''
        task_id = '89c29e6f-82e6-4a0e-8041-da1230edb7e0'
        uri = u'/v1.0/task/task/%s/graph/' % task_id
        
        res = self.invoke(self.module, uri, u'GET', data=data)
        self.logger.info(self.pp.pformat(res))

    def test_count_all_tasks(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/task/tasks/count/'
        
        res = self.invoke(self.module, uri, u'GET', data=data)
        self.logger.info(self.pp.pformat(res)) 

    def test_registered_tasks(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/task/tasks/registered/'
        
        res = self.invoke(self.module, uri, u'GET', data=data)
        self.logger.info(self.pp.pformat(res))
         
    def test_active_tasks(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/task/tasks/active/'
        
        res = self.invoke(self.module, uri, u'GET', data=data)
        self.logger.info(self.pp.pformat(res))
        
    def test_scheduled_tasks(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/task/tasks/scheduled/'
        
        res = self.invoke(self.module, uri, u'GET', data=data)
        self.logger.info(self.pp.pformat(res))
        
    def test_reserved_tasks(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/task/tasks/reserved/'
        
        res = self.invoke(self.module, uri, u'GET', data=data)
        
    def test_revoked_tasks(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/task/tasks/revoked/'
        
        res = self.invoke(self.module, uri, u'GET', data=data)
        
    def test_delete_all_tasks(self):
        global uid, seckey
        data = u''
        uri = u'/v1.0/task/tasks/'
        
        self.invoke(self.module, uri, u'DELETE', data=data)
        
    def test_delete_task(self):
        global uid, seckey
        oid = ''
        data = u''
        uri = u'/v1.0/task/task/%s/' % oid
        
        self.invoke(self.module, uri, u'DELETE', data=data)       
        
    def test_purge_tasks(self):
        global uid, seckey
        data = u''
        uri = u'/v1.0/task/tasks/purge/'
        
        self.invoke(self.module, uri, u'DELETE', data=data)          

    def test_revoke_task(self):
        global uid, seckey, task_id
        data = u''
        uri = u'/v1.0/task/task/revoke/%s/' % task_id
        
        self.invoke(self.module, uri, u'DELETE', data=data) 
        
    def test_run_job_test(self):
        global uid, seckey, task_id
        data = json.dumps({u'x':2, u'y':234, u'numbers':[2, 78, 45, 90], u'mul_numbers':[]} )
        uri = u'/v1.0/task/task/jobtest'
        self.invoke(self.module, uri, u'POST', data=data)    

    #
    # scheduler
    #
    def test_get_scheduler_entries(self):
        global uid, seckey
                
        data = u''
        uri = u'/v1.0/scheduler/entries/'
        
        res = self.invoke('monitor', uri, u'GET', data=data)
        self.logger.debug(self.pp.pformat(res))

    def test_create_scheduler_entries(self):
        global uid, seckey
                
        data = json.dumps({'name':'celery.backend_cleanup',
                           'task': 'celery.backend_cleanup',
                           'schedule': {'type':'crontab',
                                        'minute':2,
                                        'hour':'*',
                                        'day_of_week':'*',
                                        'day_of_month':'*',
                                        'month_of_year':'*'},
                           'options': {'expires': 60}})
        data = json.dumps({'name':'celery.backend_cleanup',
                           'task': 'celery.backend_cleanup',
                           'schedule': {'type':'timedelta',
                                        'minutes':1},
                           'options': {'expires': 60}})
        
        data = json.dumps({'name':'services_usage',
                           'task': 'tasks.add_services_instant_usage',
                           'schedule': {'type':'timedelta',
                                        'minutes':30},
                           'options': {'expires': 86400}})
        
        data = json.dumps({'name':'services_usage_day',
                           'task': 'tasks.add_services_day_usage',
                           'schedule': {'type':'crontab',
                                        'minute':0,
                                        'hour':0},
                           'options': {'expires': 86400}})
        
        data = json.dumps({'name':'services_usage_week',
                           'task': 'tasks.add_services_week_usage',
                           'schedule': {'type':'crontab',
                                        'minute':0,
                                        'hour':0,
                                        'day_of_week':1},
                           'options': {'expires': 86400}})
        
        data = json.dumps({'name':'services_usage_month',
                           'task': 'tasks.add_services_month_usage',
                           'schedule': {'type':'crontab',
                                        'minute':0,
                                        'hour':0,
                                        'day_of_month':1},
                           'options': {'expires': 86400}})
        
        data = json.dumps({'name':'services_usage_year',
                           'task': 'tasks.add_services_year_usage',
                           'schedule': {'type':'crontab',
                                        'minute':0,
                                        'hour':0,
                                        'month_of_year':1},
                           'options': {'expires': 86400}})

        data = json.dumps({'name':'celery.backend_cleanup',
                           'task': 'celery.backend_cleanup',
                           'schedule': {'type':'timedelta',
                                        'minutes':1},
                           'options': {'expires': 60}})

        uri = u'/v1.0/scheduler/entry/'
        
        self.invoke(self.module, uri, u'POST', data=data)

    def test_delete_scheduler_entry(self):
        global uid, seckey
                
        data = json.dumps({'name':'discover_openstack_01'})
        uri = u'/v1.0/scheduler/entry/'
        
        self.invoke(self.module, uri, u'DELETE', data=data)

def test_suite():
    tests = ['test_login',
             #'test_ping_task_manager',
             #'test_stat_task_manager',
             #'test_report_task_manager',
             ##'test_get_all_tasks',
             #'test_get_all_tasks',
             'test_get_task',
             #'test_get_task_graph',
             #'test_count_all_tasks',
             #'test_registered_tasks',
             #'test_active_tasks',
             #'test_scheduled_tasks',
             #'test_reserved_tasks',
             #'test_revoked_tasks',
             ##'test_query_task',
             ##'test_query_task_status',
             ##'test_get_task_graph',
             ##'test_query_all_tasks',
             #'test_delete_all_tasks',
             #'test_purge_tasks',
             #'test_revoke_task',
             #'test_run_job_test',
             
             
             #'test_get_scheduler_entries',
             #'test_create_scheduler_entries',
             #'test_delete_scheduler_entry',
             
             
             'test_logout',
            ]
    return unittest.TestSuite(map(SchedulerAPITestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])