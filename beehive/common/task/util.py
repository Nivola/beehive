"""
Created on May 16, 2017

@author: darkbk
"""
from celery.utils.log import get_task_logger
from beehive.common.task.manager import task_manager
from beehive.common.task.job import JobTask, job_task

logger = get_task_logger(__name__)


#
# multi purpose tasks
#
@task_manager.task(bind=True, base=JobTask)
@job_task()
def join_task(self, options):
    """Use this task as join task befor/after a group in the process.
    
    :param tupla options: Tupla with some useful options
    :return: id of the resource removed  
    :rtype: int
    
    options
        *options* must contains
        
        .. code-block:: python
    
            (class_name, objid, job, job id, start time, time before new query)
    """    
    # update job status
    self.update_job(status=u'PROGRESS')
    return None


@task_manager.task(bind=True, base=JobTask)
@job_task()
def start_task(self, options):
    """Use this task to close the process.
    
    :param tupla options: Tupla with some useful options
    :return: id of the resource removed  
    :rtype: int
    
    options
        *options* must contains
        
        .. code-block:: python
    
            (class_name, objid, job, job id, start time, time before new query)
    """    
    # update job status
    # self.logger.warn(u'START TASK - %s:%s' % (self.name, self.request.id))
    self.update(u'STARTED', msg=u'START TASK')
    self.update_job(status=u'PROGRESS')
    return None


@task_manager.task(bind=True, base=JobTask)
@job_task()
def end_task(self, options):
    """Use this task to close the process.
    
    :param tupla options: Tupla with some useful options
    :return: id of the resource removed  
    :rtype: int
    
    options
        *options* must contains
        
        .. code-block:: python
    
            (class_name, objid, job, job id, start time, time before new query)
    """    
    # update job status
    params = self.get_shared_data()
    # self.logger.warn(u'STOP TASK - %s:%s' % (self.name, self.request.id))
    self.update(u'SUCCESS', msg=u'END TASK')
    self.update_job(params=params, status=u'SUCCESS')
    return None