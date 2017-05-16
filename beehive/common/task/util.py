'''
Created on May 16, 2017

@author: darkbk
'''
from celery.utils.log import get_task_logger
from beehive.common.task.manager import task_manager
from beehive.common.task.job import JobTask, job_task

logger = get_task_logger(__name__)

#
# multi purpose tasks
#
@task_manager.task(bind=True, base=JobTask)
@job_task(module='SchedulerModule')
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
    self.update(u'PROGRESS')
    return None

@task_manager.task(bind=True, base=JobTask)
@job_task(module=u'SchedulerModule')
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
    self.update(u'PROGRESS')
    return None

@task_manager.task(bind=True, base=JobTask)
@job_task(module=u'SchedulerModule')
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
    self.update(u'SUCCESS')
    return None