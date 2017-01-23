'''
Created on Apr 27, 2015

@author: darkbk
'''
import unittest
import datetime
import time
from tests.test_util import run_test, CloudapiTestCase
from gibboncloudapi.common import ProcessDbManager
from gibbonutil.db import TransactionError, QueryError
from gibboncloudapi.util.data import operation
from gibbonutil.simple import id_gen

class ProcessDbManagerTestCase(CloudapiTestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        db_session = self.open_mysql_session(self.db_uri)
        operation.session = db_session()
        self.manager = ProcessDbManager()
        operation.transaction = 0        
        
    def tearDown(self):
        operation.session.close()
        CloudapiTestCase.tearDown(self)

    def test_create_table(self):       
        ProcessDbManager.create_table(self.db_uri)

    def test_remove_table(self):       
        ProcessDbManager.remove_table(self.db_uri)          

    def test_set_initial_data(self):       
        self.manager.set_initial_data()

    #
    # task type
    #
    def test_add_task_type(self):
        res = self.manager.add_task_type('start', 'StartTask', type='SYS', desc='')
        res = self.manager.add_task_type('stop', 'StopTask', type='SYS', desc='')
        res = self.manager.add_task_type('task1', 'Task1', type='SYS', desc='')
        res = self.manager.add_task_type('task2', 'Task2', type='SYS', desc='')
        res = self.manager.add_task_type('dummytask', 'TaskDummy', type='SYS', desc='')
    
    def test_get_task_types(self):
        res = self.manager.get_task_types()
        res = self.manager.get_task_types(name='start')

    def test_update_task_type(self):
        res = self.manager.update_task_type(name='dummytask', new_name='dummytask2')
        
    def test_remove_task_types(self):
        res = self.manager.remove_task_types(name='dummytask2')

    #
    # process
    #
    def test_add_process(self):
        res = self.manager.add_process('proc1', '')
        res = self.manager.add_process('proc2', '')
        res = self.manager.add_process('dummyproc', '')
    
    def test_get_processes(self):
        res = self.manager.get_processes()
        res = self.manager.get_processes(name='proc1')

    def test_update_process(self):
        res = self.manager.update_process(name='dummyproc', new_name='dummyproc2')

    def test_remove_process(self):
        res = self.manager.remove_process(name='dummyproc2')

    #
    # task
    #
    def test_add_task(self):
        start = self.manager.get_task_types(name='start')[0]
        task1 = self.manager.get_task_types(name='task1')[0]
        task2 = self.manager.get_task_types(name='task2')[0]
        stop = self.manager.get_task_types(name='stop')[0]
        process = self.manager.get_processes(name='proc1')[0]
        self.manager.add_task(start, process, next_tasks=None)
        self.manager.add_task(task1, process, next_tasks=None)
        self.manager.add_task(task2, process, next_tasks=None)
        self.manager.add_task(stop, process, next_tasks=None)

    def test_update_task(self):
        process = self.manager.get_processes(name='proc1')[0]
        task1 = self.manager.get_tasks(name='task1', process=process)[0]
        task2 = self.manager.get_tasks(name='task2', process=process)[0]
        stop = self.manager.get_tasks(name='stop', process=process)[0]
        self.manager.update_task(name='start', process=process, 
                                 next_tasks="%s,%s" % (task1.id, task2.id))
        self.manager.update_task(name='task1', process=process, next_tasks="%s" % stop.id)
        self.manager.update_task(name='task2', process=process, next_tasks="%s" % stop.id)

    def test_get_tasks(self):
        res = self.manager.get_tasks()
        process = self.manager.get_processes(name='proc1')[0]
        res = self.manager.get_tasks(process=process)
        res = self.manager.get_tasks(name='start', process=process)

    def test_remove_tasks(self):
        process = self.manager.get_processes(name='proc1')[0]
        res = self.manager.remove_tasks(process)

    def test_create_workflow(self):
        workflow = [('start', 'task1,task2'), ('task1', 'stop'), 
                    ('task2', 'stop'), ('stop', None)]
        process = self.manager.get_processes(name='proc2')[0]
        res = self.manager.create_workflow(process, workflow)
    
    def test_get_workflow(self):
        process = self.manager.get_processes(name='proc1')[0]
        res = self.manager.get_workflow(process)
    
    #
    # process instance
    #
    def test_add_process_instance(self):
        pid = 12345
        process = self.manager.get_processes(name='proc1')[0]
        self.manager.add_process_instance(pid, process)
        pid = 123456
        process = self.manager.get_processes(name='proc2')[0]
        self.manager.add_process_instance(pid, process)
        
    def test_get_process_instances(self):
        res = self.manager.get_process_instances()
        res = self.manager.get_process_instances(name='proc1')
        res = self.manager.get_process_instances(status=0)
    
    def test_get_process_instance_workflow(self):
        res = self.manager.get_process_instance_workflow(12345)
    
    def test_update_process_status(self):
        time.sleep(1)
        res = self.manager.update_process_status(1, 1, 1)
        
    def test_set_current_tasks(self):
        res = self.manager.set_current_tasks(1, '3')
    
    #
    # task instance
    #
    def test_add_task_instance(self):
        process = self.manager.get_processes(name='proc1')[0]
        tasks = self.manager.get_tasks(process=process)
        proc_inst = self.manager.get_process_instances(oid=12345)[0]
        self.manager.add_task_instance(tasks[0], proc_inst)
        self.manager.add_task_instance(tasks[1], proc_inst)
        self.manager.add_task_instance(tasks[2], proc_inst)
        
        process = self.manager.get_processes(name='proc2')[0]
        tasks = self.manager.get_tasks(process=process)
        proc_inst = self.manager.get_process_instances(oid=123456)[0]
        self.manager.add_task_instance(tasks[0], proc_inst)
        self.manager.add_task_instance(tasks[1], proc_inst)
        self.manager.add_task_instance(tasks[2], proc_inst)        
        
    def test_get_task_instances(self):
        self.manager.get_task_instances()
        process = self.manager.get_process_instances(oid=12345)[0]
        tasks = self.manager.get_task_instances(process=process)
        task2 = self.manager.get_tasks(name='task2', 
                                       process=self.manager.get_processes(name='proc1')[0])[0]
        tasks = self.manager.get_task_instances(process=process, task=task2)

    def test_update_task_status(self):
        self.manager.update_task_status(1, 1, 1.0, 'running')

def test_suite():
    tests = ['test_remove_table',
             'test_create_table',
             'test_set_initial_data',
             # task type
             'test_add_task_type',
             'test_get_task_types',
             'test_update_task_type',
             'test_remove_task_types',
             # process
             'test_add_process',             
             'test_get_processes',
             'test_update_process',
             'test_remove_process',
             # task
             'test_add_task',
             'test_update_task',             
             'test_get_tasks',
             'test_get_workflow',
             #'test_remove_tasks',
             'test_create_workflow',
             'test_get_workflow',
             # process instance
             'test_add_process_instance',
             'test_get_process_instances',
             'test_get_process_instance_workflow',
             'test_update_process_status',
             'test_set_current_tasks',
             # task instance
             'test_add_task_instance',
             'test_get_task_instances',
             'test_update_task_status',
            ]
    return unittest.TestSuite(map(ProcessDbManagerTestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])