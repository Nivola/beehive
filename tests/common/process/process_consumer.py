'''
Created on Sep 2, 2013

@author: darkbk
'''
import unittest
import gevent
import time
from tests.test_util import run_test, CloudapiTestCase
from gibboncloudapi.common import ProcessDbManager
from gibbonutil.db import TransactionError, QueryError
from gibboncloudapi.util.data import operation
from gibbonutil.simple import id_gen
from gibboncloudapi.common import ProcessHelper
from gibboncloudapi.common import EventProducer
from gibboncloudapi.common.process.manager2 import ProcessEventProducerRedis

pid = None

class ProcessEventConsumerTestCase(CloudapiTestCase):
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
        operation.session.close()
        CloudapiTestCase.tearDown(self)

    def test_create_table(self):       
        ProcessDbManager.create_table(self.db_uri)

    def test_remove_table(self):       
        ProcessDbManager.remove_table(self.db_uri)          

    def test_set_initial_data(self):       
        self.manager.set_initial_data()
        
        res = self.manager.add_task_type('start', 'gibboncloudapi.common.process.manager2.StartTask', type='SYS', desc='')
        res = self.manager.add_task_type('stop', 'gibboncloudapi.common.process.manager2.StopTask', type='SYS', desc='')
        res = self.manager.add_task_type('task1', 'gibboncloudapi.common.process.manager2.DummyTask', type='SYS', desc='')
        res = self.manager.add_task_type('task2', 'gibboncloudapi.common.process.manager2.UserTask', type='USER', desc='')
        res = self.manager.add_task_type('dummytask', 'TaskDummy', type='SYS', desc='')

        name = 'proc1'
        desc = 'proc1'
        workflow = [('start', 'task1'), ('task1', 'task2'), ('task2', 'stop'), ('stop', None)]
        self.helper.create_process(name, desc, workflow)
        
    def test_get_processes(self):
        self.helper.get_processes()
        procs = self.helper.get_processes(name='proc1')
        self.logger.info(procs)    
        
    def test_create_process_instance(self):
        global pid
        pid = id_gen()
        data = {'k1':'p1'}
        self.event_producer.create_process('proc1', pid, data)
        time.sleep(2)

    def test_get_process_instances(self):
        global pid        
        self.helper.get_process_instances(pid=pid)
        
    def test_ack_task(self):
        global pid
        time.sleep(20)
        #pid = 22337010
        procinst = self.helper.get_process_instances(pid=pid)[0]
        tid = int(procinst['current_task'])
        self.event_producer.resume_task(pid, tid, ['ciao'])

def test_suite():
    tests = ['test_remove_table',
             'test_create_table',
             'test_set_initial_data',
             'test_get_processes',
             'test_create_process_instance',
             #'test_get_process_instances',
             'test_ack_task',
            ]
    #tests = ['test_ack_task']
    return unittest.TestSuite(map(ProcessEventConsumerTestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])