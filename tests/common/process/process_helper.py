'''
Created on Sep 2, 2013

@author: darkbk
'''
import unittest
import gevent
from tests.test_util import run_test, CloudapiTestCase
from gibboncloudapi.common import ProcessDbManager
from gibbonutil.db import TransactionError, QueryError
from gibboncloudapi.util.data import operation
from gibbonutil.simple import id_gen
from gibboncloudapi.common import ProcessHelper
from gibboncloudapi.common import EventProducer
from gibboncloudapi.common.process.manager2 import ProcessEventProducerRedis

pid = None

class ProcessHelperTestCase(CloudapiTestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        #db_session = self.open_mysql_session(self.db_uri)
        #operation.session = db_session()
        #self.manager = EventDbManager()
        #host = '158.102.160.234'
        #port = 5500
        #self.client = EventProducer(host, port)
        db_session = self.open_mysql_session(self.db_uri)
        operation.session = db_session()
        operation.transaction = 0
        
        self.manager = ProcessDbManager()
        self.helper = ProcessHelper()
        self.event_producer = ProcessEventProducerRedis(self.redis, 'cloudapi.process.event')
        
    def tearDown(self):
        #operation.session.close()
        CloudapiTestCase.tearDown(self)

    def test_create_table(self):       
        ProcessDbManager.create_table(self.db_uri)

    def test_remove_table(self):       
        ProcessDbManager.remove_table(self.db_uri)          

    def test_set_initial_data(self):       
        self.manager.set_initial_data()
        
        res = self.manager.add_task_type('start', 'StartTask', type='SYS', desc='')
        res = self.manager.add_task_type('stop', 'StopTask', type='SYS', desc='')
        res = self.manager.add_task_type('task1', 'gibboncloudapi.common.process.manager2.ProcessTask', type='SYS', desc='')
        res = self.manager.add_task_type('task2', 'Task2', type='SYS', desc='')
        res = self.manager.add_task_type('dummytask', 'TaskDummy', type='SYS', desc='')        

    '''
    def test_create_process(self):
        name = 'proc1'
        desc = 'proc1'
        workflow = [('start', 'task1,task2'), ('task1', 'stop'), 
                    ('task2', 'stop'), ('stop', None)]
        self.helper.create_process(name, desc, workflow)
        
    def test_get_processes(self):
        self.helper.get_processes()
        procs = self.helper.get_processes(name='proc1')
        self.logger.info(procs)
    '''
    
    def test_create_process_instance(self):
        global pid
        procinst = self.helper.create_process_instance('proc1')
        pid = procinst.id
    
    def test_start_process_instance(self):
        global pid
        self.helper.start_process_instance(pid)

    def test_create_task_instance(self):
        global pid
        name = 'task1'
        thread = self.helper.create_task_instance(pid, name, self.event_producer)
        gevent.joinall([thread])

    def test_get_process_instances(self):
        global pid
        pid = None
        proc = self.helper.get_process_instances(pid=pid)
        self.pp.pprint(proc)

def test_suite():
    tests = ['test_remove_table',
             'test_create_table',
             'test_set_initial_data',
             'test_create_process',
             'test_get_processes',
             'test_create_process_instance',
             'test_start_process_instance',
             'test_create_task_instance',
             'test_get_process_instances',
            ]
    tests = ['test_get_process_instances',]
    return unittest.TestSuite(map(ProcessHelperTestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])