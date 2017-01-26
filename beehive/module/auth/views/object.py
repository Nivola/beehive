'''
Created on Jan 26, 2017

@author: darkbk
'''
from re import match
from beecell.simple import get_value
from beehive.common.apimanager import ApiView, ApiManagerError
from flask import request

class ObjectApiView(ApiView):
    """Object api. Use to query auth objects, types and actions.
    
    *Headers*:
    
    * **uid** : id of the client identity.
    * **sign**: request signature. Used by server to identify verify client identity.
    * **Accept**: response mime type. Supported: json, bson, xml
    
    *Uri*:

    * ``/api/auth/object/``, **GET**, Get all objects
    * ``/api/auth/object/V:*.*.*.*/``, **GET**, Get objects by unique id
    * ``/api/auth/object/T:auth/``, **GET**, Get objects by type
    * ``/api/auth/object/D:cloudstack.org.grp.volume/``, **GET**, Get objects by definition
    * ``/api/auth/object/perm/``, **GET**, Get all permissions
    * ``/api/auth/object/perm/<id>``, **GET**, Get permission by id <id>
    * ``/api/auth/object/``, **POST**, Add objects::
    
        [(objtype, definition, objid), (objtype, definition, objid)]

    * ``/api/auth/object/<id>/``, **DELETE**, Delete object by <id>
    * ``/api/auth/object/type/``, **GET**, Get types
    * ``/api/auth/object/type/T:resource/``, **GET**, Get type by type    
    * ``/api/auth/object/type/D:orchestrator.org.area.prova/``, **GET**, Get type by definition
    * ``/api/auth/object/type/``, **POST**, Add objects::
    
        [('resource', 'orchestrator.org.area.prova', 'ProvaClass')]

    * ``/api/auth/object/typ/<id>/``, **DELETE**, Delete object type by <id>
    * ``/api/auth/object/action/``, **GET**, Get object actions
    """
    def get_object(self, controller, oid):
        obj = controller.get(oid=oid)
        if len(obj) == 0:
            raise ApiManagerError(u'Object %s not found' % oid, code=404)
        return obj[0]

#
# object api
#
class ListObjects(ObjectApiView):
    def dispatch(self, controller, name, data, *args, **kwargs):
        headers = request.headers
        objid = get_value(headers, u'objid', None)
        objtype = get_value(headers, u'objtype', None)
        objdef = get_value(headers, u'objdef', None)
        # convert _ in //
        if objid is not None:
            objid = objid.replace(u'_', u'//')
        res = controller.get(objtype=objtype, objdef=objdef, objid=objid)     
        
        resp = {u'objects':res,
                u'count':len(res)}
        return resp
    
class CreateObject(ObjectApiView):
    """ 
    {
        u'objects':[
            (objtype, objdef, objid),..
        ]
    }
    """
    def dispatch(self, controller, data, *args, **kwargs):
        objects = get_value(data, u'objects', None, exception=True)
        if not isinstance(objects, list):
            raise ApiManagerError(u'Objects must be a list')
        
        resp = controller.add(data)
        return (resp, 201)
    
class DeleteObject(ObjectApiView):
    """ TODO
    """
    def dispatch(self, controller, data, oid, *args, **kwargs):
        resp = controller.remove(oid=oid)
        return (resp, 204)

class ListObjectPerms(ObjectApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        headers = request.headers
        objid = get_value(headers, u'objid', None)        
        objtype = get_value(headers, u'objtype', None)
        objdef = get_value(headers, u'objdef', None)
        action = get_value(headers, u'action', None)
        res = controller.get_permission(objid=objid, 
                                        objtype=objtype, 
                                        objdef=objdef, 
                                        action=action)
        resp = {u'object_perms':res,
                u'count':len(res)}        
        return resp
    
class GetObjectPerm(ObjectApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        res = controller.get_permission(permission_id=oid)

        resp = {u'object_perm':res}        
        return resp    

#
# object type api
#
class ListObjectTypes(ObjectApiView):
    def dispatch(self, controller, name, data, *args, **kwargs):
        headers = request.headers
        objtype = get_value(headers, u'objtype', None)
        objdef = get_value(headers, u'objdef', None)
        res = controller.get_type(objtype=objtype, objdef=objdef)
        
        resp = {u'object_types':res,
                u'count':len(res)}
        return resp
    
class CreateObjectType(ObjectApiView):
    """Create object types
    {
        u'object_types':[
            (objtype, objdef),..
        ]
    }
    """
    def dispatch(self, controller, data, *args, **kwargs):
        data = get_value(data, u'object_types', None, exception=True)
        if not isinstance(data, list):
            raise ApiManagerError(u'Objects must be a list')        
        
        resp = controller.add_types(data)
        return (resp, 201)
    
class DeleteObjectType(ObjectApiView):
    """ TODO
    """
    def dispatch(self, controller, data, oid, *args, **kwargs):
        resp = controller.remove_type(oid=oid)
        return (resp, 204)
    
#
# object action api
#
class ListObjectActions(ObjectApiView):
    def dispatch(self, controller, name, data, *args, **kwargs):
        res = controller.get_type()
        resp = {u'object_actions':res,
                u'count':len(res)}
        return resp    

class BaseAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            (u'auth/objects', u'GET', ListObjects, {}),
            (u'auth/object', u'POST', CreateObject, {}),
            (u'auth/object/<oid>', u'DELETE', DeleteObject, {}),
            (u'auth/object/perms', u'GET', ListObjectPerms, {}),
            (u'auth/object/perms/<oid>', u'GET', GetObjectPerm, {}),
            
            (u'auth/object/types', u'GET', ListObjectTypes, {}),
            (u'auth/object/type', u'POST', CreateObjectType, {}),
            (u'auth/object/type/<oid>', u'DELETE', DeleteObjectType, {}),
            
            (u'auth/object/actions', u'GET', ListObjectActions, {}),            
        ]

        ApiView.register_api(module, rules)