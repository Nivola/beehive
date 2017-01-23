'''
Created on Sep 2, 2013

@author: darkbk
'''
from tests.test_util import run_test, CloudapiTestCase
import unittest
import redis
import gevent
import urllib2
import json
import time
from gibboncloudapi.common import JobManager, job_wrapper, JobStatus, JobError

class JobTestCase(CloudapiTestCase):
    """To execute this test you need a mysql instance, a user and a 
    database associated to the user.
    """
    def setUp(self):
        CloudapiTestCase.setUp(self)
        host = '127.0.0.1'
        port = 6379
        db = 0
        self.redis_manager = redis.StrictRedis(host=host, port=int(port), db=int(db))
        self.job_manager = JobManager(self.redis_manager, 'cloudapi.message', 2, 2, 10)
        
    def tearDown(self):
        CloudapiTestCase.tearDown(self)

    def test_get_jobs(self):
        jobs = self.job_manager.get_jobs()
        self.logger.debug(jobs)

    def test_get_job(self):
        self.job_manager.get_job('ceeb122641434ebe867edccc4b19fe30')
        
    def test_kill_job(self):
        self.job_manager.kill_job('ceeb122641434ebe867edccc4b19fe30')

    def test_delete_job(self):
        self.job_manager.delete_job('ceeb122641434ebe867edccc4b19fe30')

    def test_run_job(self):
        # job task
        @job_wrapper(self.job_manager)
        def task(start, params):
            res = []
            try:
                job_id = params['jobid']
                self.logger.debug('Enter test task %s' % (job_id))
                # task
                for i in range(0, 3):
                    # fetch url
                    request = urllib2.Request(params['uri'])
                    # set proxy
                    if 'proxy' in params and params['proxy'] is not None:      
                        request.set_proxy(params['proxy'], 'http')
                        request.set_proxy(params['proxy'], 'https')
                    
                    response = urllib2.urlopen(request)
                    result = response.read()
                    res.append(result)
    
                    # update job status
                    elapsed = round(time.time() - start, 4)
                    self.job_manager.update_job(job_id, JobStatus.RUN, elapsed)
                    
                    gevent.sleep(2)
            except Exception as ex:
                raise JobError(str(ex))
            
            self.logger.debug('Exit test task %s: %s' % (job_id, res))
            return res
        
        def count():
            for i in range(0, 3):
                self.job_manager.count_active_jobs()
                gevent.sleep(2)
                
        def kill(job_id):
            gevent.sleep(2)
            self.job_manager.kill_job(job_id) 
        
        # create new job
        job_type = 'test'
        job_cmd = 'task'
        job_data = ['1', 'a']
        job1 = self.job_manager.create_job(job_type, job_cmd, job_data)
        job2 = self.job_manager.create_job(job_type, job_cmd, job_data)   
        
        # get job
        #job = self.job_manager.get_job(job.key)

        # start job
        params = {'jobid':0, 'uri':'http://www.thomas-bayer.com/sqlrest/CUSTOMER/3/', 'proxy':None}
        (data, thread1) = self.job_manager.start_job(job1.key, task, params)
        (data, thread2) = self.job_manager.start_job(job2.key, task, params)
        #thread2 = gevent.spawn(self.job_manager.get_jobs)
        thread3 = gevent.spawn(kill, job1.key)
        thread4 = gevent.spawn(count)
        gevent.joinall([thread1, thread2, thread3, thread4])
        self.job_manager.count_active_jobs()

def test_suite():
    tests = ['test_get_jobs',
             #'test_get_job',
             #'test_kill_job',
             #'test_delete_job',
             #'test_run_job',
            ]
    return unittest.TestSuite(map(JobTestCase, tests))

if __name__ == '__main__':
    run_test([test_suite()])