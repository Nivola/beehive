'''
Created on Aug 13, 2014

@author: darkbk
'''
import ujson as json
from flask import request
from gibboncloudapi.module.base import MethodView, ApiManagerError
from gibboncloudapi.util.data import operation

class ConfigAPI(MethodView):
    """**ConfigAPI**
    
    Configuration api. Use to query systems configurations.
    
    *Headers:*
    
    * **uid** : id of the client identity.
    * **sign**: request signature. Used by server to identify verify client identity.
    * **Accept**: response mime type. Supported: json, bson, xml
    
    *Uri:*

    * ``/config/<webapp>``, *GET*, Get configurations
    
    *Raise*::
    
        {'status':'error', 
         'api':<http path>, 
         'exception':<exception>,
         'code':<error code>, 
         'data':<error data>}    
    """
    decorators = []

    def get(self, webapp, module=None):
        """"""
        resp = {}
        try:
            # open database session.
            dbsession = module.get_session()    
            perms = operation.perms
            controller = module.get_controller()

            if webapp == 'cloudapi':
                #logging configuration
                #resp['logging'] = [c.info() for c in controller.get_log_config(webapp)]
                
                #redis configuration
                resp['redis'] = controller.get_config(app=webapp, 
                                                      group='redis', 
                                                      name='redis_01')[0].value

                # security configuration
                resp['authentication'] = [c.info() for c in controller.get_auth_config()]
    
                # tcp proxy configuration
                tcp_proxy = controller.get_config(app=webapp, group='tcpproxy')[0]
                resp['tcp_proxy'] = {'id':tcp_proxy.name, 'ip':tcp_proxy.value}
                
                # http proxy configuration
                tcp_proxy = controller.get_config(app=webapp, group='httpproxy')[0]
                resp['http_proxy'] = {'id':tcp_proxy.name, 'ip':tcp_proxy.value}
                
                # endpoint configuration
                endpoints = controller.get_config(app=webapp, group='endpoint')
                resp['endpoint'] = {e.name:json.loads(e.value) for e in endpoints}
                
                # queue configuration
                queues = controller.get_config(app=webapp, group='queue')
                resp['queue'] = {e.name:json.loads(e.value) for e in queues}                          
            else:
                for item in controller.get_config(app=webapp):
                    try:
                        value = json.loads(item.value)
                    except:
                        value = item.value
                    if item.group in resp:
                        resp[item.group].append({item.name:value})
                    else:
                        resp[item.group] = [{item.name:value}]

            module.release_session(dbsession)
        except ApiManagerError as e:
            #self.logger.error(e)
            return self.get_error('ApiManagerError', e.code, e.value)
        
        self.logger.debug('Get %s configuration' % webapp)

        return self.get_response(resp)
    
    def post(self, objs, orchid, vmid, par1):
        """"""
        data = json.loads(request.data)
        return self.get_error('NotImplementedError', 2000, '')

    def delete(self, objs, orchid, vmid, par1):
        """"""
        return self.get_error('NotImplementedError', 2000, '')

    def put(self, objs, orchid, vmid, par1):
        """"""
        return self.get_error('NotImplementedError', 2000, '')
    
    @staticmethod
    def register_api(module):
        app = module.api_manager.app
        api = '/api/config/<webapp>/'
        api_view = ConfigAPI.as_view('config_api')
        
        # view methods
        app.add_url_rule(api, view_func=api_view, methods=['GET'],
                         defaults={'module':module})
        app.add_url_rule(api+'<par1>/', view_func=api_view, methods=['GET'],
                         defaults={'module':module})
        
        # create methods
        app.add_url_rule(api, view_func=api_view, methods=['POST'],
                         defaults={'module':module})
        
        # update methods
        app.add_url_rule(api, view_func=api_view, methods=['PUT'],
                         defaults={'module':module})
        
        # delete methods
        app.add_url_rule(api, view_func=api_view, methods=['DELETE'],
                         defaults={'module':module})