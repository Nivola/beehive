'''
Created on May 5, 2017

@author: darkbk
'''
import datetime
from celery.utils.log import get_task_logger
from beehive.common.apiclient import BeehiveApiClient
from beehive.common.task.job import Job, task_local, job, JobTask, job_task
from beehive.module.catalog.controller import Catalog
from beehive.module.catalog.common import CatalogEndpoint
from beehive.common.task.manager import task_manager
from beehive.common.task.util import end_task, start_task
from beehive.module.auth.controller import User, Role, Group

logger = get_task_logger(__name__)

#
# AuthJob
#
class AuthJob(Job):
    """AuthJob class.
    
    :param list args: Free job params passed as list
    :param dict kwargs: Free job params passed as dict
    """
    abstract = True
    ops = [
        User,
        Role,
        Group,
    ]
    
    def __init__(self, *args, **kwargs):
        Job.__init__(self, *args, **kwargs)

class AuthJobTask(JobTask):
    """AuthJobTask class.
    
    :param list args: Free job params passed as list
    :param dict kwargs: Free job params passed as dict          
    """
    abstract = True
    ops = [
        User,
        Role,
        Group,
    ]
    
    def __init__(self, *args, **kwargs):
        JobTask.__init__(self, *args, **kwargs)
        
        self.apiclient = BeehiveApiClient([], None, None, None)

    def get_endpoints(self, oid=None):
        """Get all endpoints
        """
        '''try:
            endpoints = task_local.controller.manager.get_endpoints()
        except:
            endpoints = []
            logger.debug(u'Get endpoints: %s' % endpoints)'''
        endpoints = task_local.controller.get_endpoints(oid=oid)
        logger.debug(u'Get endpoints: %s' % endpoints)
        return endpoints
    
    def ping_endpoint(self, endpoint):
        """Ping endpoint
        
        :param endpoint: CatalogEndpoint instance
        """
        uri = endpoint.model.uri
        res = self.apiclient.ping(endpoint=uri)
        logger.warn(u'Ping endpoint %s: %s' % (uri, res))
        return res      

#
# auth tasks
#
@task_manager.task(bind=True, base=AuthJob)
@job(entity_class=Catalog, module=u'AuthModule', delta=1)
def disable_expired_users(self, objid, params):
    """Disable expired users
    
    :param objid: objid of the resource. Ex. 110//2222//334//*
    :param params: task input params
    :return: True  
    :rtype: bool    
    
    Params
        Params contains:
        
        * **cid**: container id

        
        .. code-block:: python
    
            {
                u'cid':..,

            }
    """
    ops = self.get_options()
    self.set_shared_data(params)
    self.set_operation()

    Job.create([
        end_task,
        disable_expired_users_task,
        start_task,
    ], ops).delay()
    return True    

@task_manager.task(bind=True, base=AuthJobTask)
@job_task(module=u'AuthModule')
def disable_expired_users_task(self, options):
    """Disable expired users - task
    """
    self.set_operation()
    self.get_session()
    expiry_date = datetime.datetime.today()
    res = task_local.controller.dbauth.expire_users(expiry_date)
    self.release_session()
    return res

@task_manager.task(bind=True, base=AuthJob)
@job(entity_class=Catalog, module=u'AuthModule', delta=1)
def remove_expired_roles_from_users(self, objid, params):
    """Remove expired roles from users
    
    :param objid: objid of the resource. Ex. 110//2222//334//*
    :param params: task input params
    :return: True  
    :rtype: bool    
    
    Params
        Params contains:
        
        * **cid**: container id

        
        .. code-block:: python
    
            {
                u'cid':..,

            }
    """
    ops = self.get_options()
    self.set_shared_data(params)
    self.set_operation()
    
    Job.create([
        end_task,
        remove_expired_roles_from_users_task,
        start_task,
    ], ops).delay()
    return True

@task_manager.task(bind=True, base=AuthJobTask)
@job_task(module=u'AuthModule')
def remove_expired_roles_from_users_task(self, options):
    """Remove expired roles from users - task
    """
    self.set_operation()
    self.get_session()
    expiry_date = datetime.datetime.today()
    res = task_local.controller.dbauth.remove_expired_user_role(expiry_date)
    self.release_session()
    return res

