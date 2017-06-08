'''
Created on May 5, 2017

@author: darkbk
'''
from celery.utils.log import get_task_logger
from beehive.common.apiclient import BeehiveApiClient
from beehive.common.task.job import Job, task_local, job, JobTask, job_task
from beehive.module.catalog.controller import Catalog, CatalogEndpoint
from beehive.common.task.manager import task_manager
from beehive.common.task.util import end_task, start_task

logger = get_task_logger(__name__)

#
# CatalogJob
#
class CatalogJob(Job):
    """CatalogJob class.
    
    :param list args: Free job params passed as list
    :param dict kwargs: Free job params passed as dict
    """
    abstract = True
    ops = [
        Catalog,
        CatalogEndpoint,
    ]
    
    def __init__(self, *args, **kwargs):
        Job.__init__(self, *args, **kwargs)
        
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

class CatalogJobTask(JobTask):
    """CatalogJobTask class.
    
    :param list args: Free job params passed as list
    :param dict kwargs: Free job params passed as dict          
    """
    abstract = True
    ops = [
        Catalog,
        CatalogEndpoint,
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
    
    def remove_endpoint(self, endpoint):
        """Remove endpoint
        
        :param endpoint: CatalogEndpoint instance
        """
        res = endpoint.delete()
        logger.debug(u'Delete endpoint: %s' % endpoint.oid)
        return res    

#
# catalog refresh tasks
#
@task_manager.task(bind=True, base=CatalogJob)
@job(entity_class=Catalog, module=u'CatalogModule', delta=1)
def refresh_catalog(self, objid, params):
    """Create availability zone.
    
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
    
    # get all endpoints
    self.get_session()
    endpoints = self.get_endpoints()
    self.release_session()
    
    g_endpoints = []
    for endpoint in endpoints:
        g_endpoints.append(ping_endpoint.si(ops, endpoint.oid))
    
    Job.create([
        end_task,
        g_endpoints,
        start_task,
    ], ops).delay()
    return True    

@task_manager.task(bind=True, base=CatalogJobTask)
@job_task(module=u'CatalogModule')
def ping_endpoint(self, params, endpoint_id):
    """
    """
    self.set_operation()
    self.get_session()
    endpoint = self.get_endpoints(endpoint_id)[0]
    ping = self.ping_endpoint(endpoint)
    if ping is False:
        res = self.remove_endpoint(endpoint)
    self.release_session()
    return ping


