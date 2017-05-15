"""
Created on Jan 12, 2017

@author: darkbk
"""
from re import match
from flask import request
from beecell.simple import get_value, str2bool
from beehive.common.apimanager import ApiView, ApiManagerError

class AuthApiView(ApiView):
    def get_user(self, controller, oid):
        """
        """        
        # get obj by uuid
        if match(u'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(oid)):
            obj, total = controller.get_users(uuid=oid)
        # get link by id
        elif match(u'[0-9]+', str(oid)):
            obj, total = controller.get_users(oid=int(oid))
        # get obj by name
        else:
            obj, total = controller.get_users(name=oid)
        if total == 0:
            raise ApiManagerError(u'User %s not found' % oid, code=404)
        return obj[0]
    
    def get_role(self, controller, oid):
        """
        """        
        # get obj by uuid
        if match(u'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(oid)):
            obj, total = controller.get_roles(uuid=oid)
        # get link by id
        elif match(u'[0-9]+', str(oid)):
            obj, total = controller.get_roles(oid=int(oid))
        # get obj by name
        else:
            obj, total = controller.get_roles(name=oid)        
        if total == 0:
            raise ApiManagerError(u'Role %s not found' % oid, code=404)
        return obj[0]
    
    def get_group(self, controller, oid):
        """
        """        
        # get obj by uuid
        if match(u'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(oid)):
            obj, total = controller.get_groups(uuid=oid)
        # get link by id
        elif match(u'[0-9]+', str(oid)):
            obj, total = controller.get_groups(oid=int(oid))
        # get obj by name
        else:
            obj, total = controller.get_groups(name=oid)        
        if total == 0:
            raise ApiManagerError(u'Group %s not found' % oid, code=404)
        return obj[0]
    
    def get_object(self, controller, oid):
        obj, total = controller.objects.get(oid=oid)        
        if total == 0:
            raise ApiManagerError(u'Object %s not found' % oid, code=404)
        return obj[0]

    def get_object_perm(self, controller, oid):
        obj, total = controller.objects.get_permissions_with_roles(oid=oid)        
        if total == 0:
            raise ApiManagerError(u'Object permission %s not found' % oid, 
                                  code=404)
        return obj[0]

#
# user
#
class ListUsers(AuthApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        group = request.args.get(u'group', None)
        role = request.args.get(u'role', None)        
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        order = request.args.get(u'order', u'DESC')
        field = request.args.get(u'field', u'id')
        if field not in [u'id', u'objid', u'name']:
            field = u'id'
            
        objs, total = controller.get_users(role=role, group=group,
                                           page=int(page), size=int(size), 
                                           order=order, field=field)
        res = [r.info() for r in objs]
        resp = {u'users':res,
                u'count':len(res),
                u'page':page,
                u'total':total}         
        return resp

class GetUser(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):      
        obj = self.get_user(controller, oid)
        res = obj.info()
        #res[u'perms'] = obj.get_permissions()
        #res[u'groups'] = obj.get_groups()
        #res[u'roles'] = obj.get_roles()        
        resp = {u'user':res} 
        return resp

'''
class GetUserRoles(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        order = request.args.get(u'order', u'DESC')
        field = request.args.get(u'field', u'id')
        if field not in [u'id', u'objid', u'name']:
            field = u'id'
        
        objs, total = controller.get_roles(user=oid, page=int(page), 
                                           size=int(size), order=order, 
                                           field=field)
        res = [r.info() for r in objs]
        resp = {u'roles':res, 
                u'count':len(res),
                u'page':page,
                u'total':total}       
        return resp    
    
class GetUserPerms(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        order = request.args.get(u'order', u'DESC')
        field = request.args.get(u'field', u'id')
        if field not in [u'subsystem', u'type', u'id', u'objid', u'aid', 
                         u'action']:
            field = u'id'
        if field == u'subsystem':
            field = u'objtype'
        elif field == u'type':
            field = u'objdef' 
        
        user = self.get_user(controller, oid)
        objs, total = user.get_permissions(page=int(page), size=int(size), 
                                           order=order, field=field)

        resp = {u'perms':objs, 
                u'count':len(objs),
                u'page':page,
                u'total':total}
        return resp
    
class GetUserGroups(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        order = request.args.get(u'order', u'DESC')
        field = request.args.get(u'field', u'id')
        if field not in [u'id', u'objid', u'name']:
            field = u'id'
        
        objs, total = controller.get_groups(user=oid, page=int(page), 
                                           size=int(size), order=order, 
                                           field=field)
        res = [r.info() for r in objs]
        resp = {u'groups':res, 
                u'count':len(res),
                u'page':page,
                u'total':total}       
        return resp'''

class GetUserAtributes(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):      
        user = self.get_user(controller, oid)
        objs = user.get_attribs()
        #res = [r.info() for r in objs]
        res = objs
        resp = {u'user-attributes':res,
                u'count':len(objs)} 
        return resp

class CreateUser(AuthApiView):
    """
    if generic is True generate generic user else generate custom user
    
    :param data: {
        'user':{
            'name':, 
            'usertype':, 
            'active':True, 
            'password':None, 
            'desc':'', 
            'attribute':'', 
            'generic':True,
            'system':True
        }
    }
    """
    def dispatch(self, controller, data, *args, **kwargs):
        data = get_value(data, u'user', None, exception=True)
        username = get_value(data, u'name', None, exception=True)
        password = get_value(data, u'password', None)
        description = get_value(data, u'desc', u'User %s' % username)
        active = get_value(data, u'active', True)
        active = str2bool(active)
                           
        if u'generic' in data and data.get(u'generic') is True:
            storetype = get_value(data, u'storetype', None, exception=True)
            resp = controller.add_generic_user(username, 
                                               storetype, 
                                               password=password, 
                                               description=description)
        elif u'system' in data and data[u'system'] == True:
            resp = controller.add_system_user(username,
                                              password=password, 
                                              description=description)                
        else:
            storetype = get_value(data, u'storetype', None, exception=True)
            systype = get_value(data, u'systype', None, exception=True)
            resp = controller.add_user(username, 
                                       storetype,
                                       systype,
                                       active=active, 
                                       password=password, 
                                       description=description)
        return (resp, 201)
    
class UpdateUser(AuthApiView):
    """
    :param data: {
        'user':{
            'name':, 
            'storetype':, 
            'desc':,
            'active':, 
            'password':, 
            'roles':{'append':, 'remove':}
        }
    }
    """
    def dispatch(self, controller, data, oid, *args, **kwargs):
        data = get_value(data, u'user', None, exception=True)
        new_name = get_value(data, u'name', None)
        new_storetype = get_value(data, u'storetype', None)
        new_description = get_value(data, u'desc', None)
        new_active = get_value(data, u'active', None)
        new_password = get_value(data, u'password', None)
        role = get_value(data, u'roles', None)
        if new_active is not None:
            new_active = str2bool(new_active)
        
        user = self.get_user(controller, oid)
        
        resp = {u'update':None, u'role.append':[], u'role.remove':[]}
        
        # append, remove role
        if role is not None:
            # append role
            if u'append' in role:
                for role in role.get(u'append'):
                    res = user.append_role(role)
                    resp[u'role.append'].append(res)
        
            # remove role
            if u'remove' in role:
                for role in role.get(u'remove'):
                    res = user.remove_role(role)
                    resp[u'role.remove'].append(res)
        
        # update user
        res = user.update(new_name=new_name,
                          new_storetype=new_storetype,
                          new_description=new_description,
                          new_active=new_active, 
                          new_password=new_password)
        resp[u'update'] = res
        return resp

class CreateUserAttribute(AuthApiView):
    """
    :param: {
        'user-attribute':{
            'name':,
            'new_name':,
            'value':,
            'desc':
        }
    }
    """
    def dispatch(self, controller, data, oid, *args, **kwargs):
        data = get_value(data, u'user-attribute', None, exception=True)
        name = get_value(data, u'name', None, exception=True)
        new_name = get_value(data, u'new_name', None)
        value = get_value(data, u'value', None, exception=True)
        desc = get_value(data, u'desc', None, exception=True)
        user = self.get_user(controller, oid)
        attr = user.set_attribute(name, value=value, 
                                  desc=desc, new_name=new_name)
        resp = (attr.name, attr.value, attr.desc)
        return (resp, 201)

class DeleteUserAttribute(AuthApiView):
    def dispatch(self, controller, data, oid, aid, *args, **kwargs):
        user = self.get_user(controller, oid)
        resp = user.remove_attribute(aid)
        return (resp, 204)

class DeleteUser(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        user = self.get_user(controller, oid)
        resp = user.delete()
        return (resp, 204)

#
# role
#
class ListRoles(AuthApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        user = request.args.get(u'user', None)
        group = request.args.get(u'group', None)
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        order = request.args.get(u'order', u'DESC')
        field = request.args.get(u'field', u'id')
        if field not in [u'id', u'objid', u'name']:
            field = u'id'
                    
        objs, total = controller.get_roles(user=user, group=group, 
                                           page=int(page), size=int(size), 
                                           order=order, field=field)
        res = [r.info() for r in objs]
        resp = {u'roles':res, 
                u'count':len(res),
                u'page':page,
                u'total':total}       
        return resp

class GetRole(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):      
        obj = self.get_role(controller, oid)
        res = obj.info()      
        resp = {u'role':res} 
        return resp

'''
class GetRolePerms(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        order = request.args.get(u'order', u'DESC')
        field = request.args.get(u'field', u'id')
        if field not in [u'subsystem', u'type', u'id', u'objid', u'aid', 
                         u'action']:
            field = u'id'
        if field == u'subsystem':
            field = u'objtype'
        elif field == u'type':
            field = u'objdef' 
        
        role = self.get_role(controller, oid)
        objs, total = role.get_permissions(page=int(page), size=int(size), 
                                           order=order, field=field)

        resp = {u'perms':objs, 
                u'count':len(objs),
                u'page':page,
                u'total':total}
        return resp
    
class GetRoleUsers(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        order = request.args.get(u'order', u'DESC')
        field = request.args.get(u'field', u'id')
        if field not in [u'id', u'objid', u'name']:
            field = u'id'
            
        objs, total = controller.get_users(role=oid, page=int(page), 
                                           size=int(size), order=order, 
                                           field=field)
        res = [r.info() for r in objs]
        resp = {u'users':res,
                u'count':len(res),
                u'page':page,
                u'total':total}         
        return resp   
    
class GetRoleGroups(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        order = request.args.get(u'order', u'DESC')
        field = request.args.get(u'field', u'id')
        if field not in [u'id', u'objid', u'name']:
            field = u'id'
        
        objs, total = controller.get_groups(role=oid, page=int(page), 
                                           size=int(size), order=order, 
                                           field=field)
        res = [r.info() for r in objs]
        resp = {u'groups':res, 
                u'count':len(res),
                u'page':page,
                u'total':total}       
        return resp'''

class CreateRole(AuthApiView):
    """
    :param data: {
        u'role':{
            u'name':.., 
            u'desc':.., 
            u'type':.. [optional]
        }
    }
    
    Use type when you want to create role with pre defined permissions.
    - type = app - create an app role  
    """
    def dispatch(self, controller, data, *args, **kwargs):
        data = get_value(data, u'role', None, exception=True)
        rolename = get_value(data, u'name', None, exception=True)
        description = get_value(data, u'desc', u'Role %s' % rolename)
        rtype = get_value(data, u'type', None)
                       
        # create role with default permissions
        if rtype is not None :
            # app system role
            if rtype == u'app':
                resp = controller.add_app_role(rolename)
        # create role without default permissions
        else:
            resp = controller.add_role(rolename, description)
        return (resp, 201)
    
class UpdateRole(AuthApiView):
    """
    :param data: {
        u'role':{
            u'name':, 
            u'desc':,
            u'perms':{
                u'append':[
                    (0, 0, "resource", "cloudstack.org.grp.vm", "", 0, "use")
                ], 
                u'remove':[]}}
    }
    """
    def dispatch(self, controller, data, oid, *args, **kwargs):
        data = get_value(data, u'role', None, exception=True)
        new_name = get_value(data, u'name', None)
        new_description = get_value(data, u'desc', None)
        role_perm = get_value(data, u'perms', None)
        
        role = self.get_role(controller, oid)
        
        resp = {u'update':None, u'perm.append':None, u'perm.remove':None}
        
        # append, remove role
        if role_perm is not None:
            # append role
            if u'append' in role_perm:
                perms = []
                for perm in role_perm.get(u'append'):
                    perms.append(perm)
                res = role.append_permissions(perms)
                resp[u'perm.append'] = res
        
            # remove role
            if u'remove' in role_perm:
                perms = []
                for perm in role_perm.get(u'remove'):
                    perms.append(perm)
                res = role.remove_permissions(perms)
                resp[u'perm.remove'] = res
        
        # update role
        res = role.update(new_name=new_name, 
                          new_description=new_description)        
        resp[u'update'] = res
        return resp

class DeleteRole(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        role = self.get_role(controller, oid)
        resp = role.delete()
        return (resp, 204)

#
# group
#
class ListGroups(AuthApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        user = request.args.get(u'user', None)
        role = request.args.get(u'role', None)        
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        order = request.args.get(u'order', u'DESC')
        field = request.args.get(u'field', u'id')
        if field not in [u'id', u'objid', u'name']:
            field = u'id'
                    
        objs, total = controller.get_groups(role=role, user=user,
                                            page=int(page), size=int(size), 
                                            order=order, field=field)
        res = [r.info() for r in objs]
        resp = {u'groups':res, 
                u'count':len(res),
                u'page':page,
                u'total':total}       
        return resp

class GetGroup(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):      
        obj = self.get_group(controller, oid)
        res = obj.info()      
        resp = {u'group':res} 
        return resp

'''
class GetGroupPerms(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        order = request.args.get(u'order', u'DESC')
        field = request.args.get(u'field', u'id')
        if field not in [u'subsystem', u'type', u'id', u'objid', u'aid', 
                         u'action']:
            field = u'id'
        if field == u'subsystem':
            field = u'objtype'
        elif field == u'type':
            field = u'objdef' 
        
        group = self.get_group(controller, oid)
        objs, total = group.get_permissions(page=int(page), size=int(size), 
                                           order=order, field=field)

        resp = {u'perms':objs, 
                u'count':len(objs),
                u'page':page,
                u'total':total}
        return resp
    
class GetGroupUsers(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        order = request.args.get(u'order', u'DESC')
        field = request.args.get(u'field', u'id')
        if field not in [u'id', u'objid', u'name']:
            field = u'id'
            
        objs, total = controller.get_users(group=oid, page=int(page), 
                                           size=int(size), order=order, 
                                           field=field)
        res = [r.info() for r in objs]
        resp = {u'users':res,
                u'count':len(res),
                u'page':page,
                u'total':total}         
        return resp
'''

class CreateGroup(AuthApiView):
    """
    :param data: {
        u'group':{
            u'name':.., 
            u'desc':.., 
        }
    }
    
    Use type when you want to create group with pre defined permissions.
    - type = app - create an app group  
    """
    def dispatch(self, controller, data, *args, **kwargs):
        data = get_value(data, u'group', None, exception=True)
        groupname = get_value(data, u'name', None, exception=True)
        description = get_value(data, u'desc', u'Group %s' % groupname)
                       
        resp = controller.add_group(groupname, description)
        return (resp, 201)
    
class UpdateGroup(AuthApiView):
    """
    :param data: {
        u'group':{
            u'name':, 
            u'desc':,
            u'users':{
                u'append':[<id>, <uuid>, <name>], 
                u'remove':[<id>, <uuid>, <name>]
            },
            u'roles':{
                u'append':[<id>, <uuid>, <name>], 
                u'remove':[<id>, <uuid>, <name>]
            }            
        }
    }
    """
    def dispatch(self, controller, data, oid, *args, **kwargs):
        data = get_value(data, u'group', None, exception=True)
        new_name = get_value(data, u'name', None)
        new_description = get_value(data, u'desc', None)
        group_role = get_value(data, u'roles', None)
        group_user = get_value(data, u'users', None)
        
        group = self.get_group(controller, oid)
        
        resp = {u'update':None,
                u'role.append':[], u'role.remove':[], 
                u'user.append':[], u'user.remove':[]}
        
        # append, remove role
        if group_role is not None:
            # append role
            if u'append' in group_role:
                for role in group_role.get(u'append'):
                    res = group.append_role(role)
                    resp[u'role.append'].append(res)
        
            # remove role
            if u'remove' in group_role:
                for role in group_role.get(u'remove'):
                    res = group.remove_role(role)
                    resp[u'role.remove'].append(res)
                    
        # append, remove user
        if group_user is not None:
            # append user
            if u'append' in group_user:
                for user in group_user.get(u'append'):
                    res = group.append_user(user)
                    resp[u'user.append'].append(res)
        
            # remove user
            if u'remove' in group_user:
                for user in group_user.get(u'remove'):
                    res = group.remove_user(user)
                    resp[u'user.remove'].append(res)                    
        
        # update group
        res = group.update(new_name=new_name, 
                           new_description=new_description)        
        resp[u'update'] = res
        return resp

class DeleteGroup(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        group = self.get_group(controller, oid)
        resp = group.delete()
        return (resp, 204)
    
#
# object
#
class ListObjects(AuthApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        objtype = request.args.get(u'subsystem', None)
        objdef = request.args.get(u'type', None)
        objid = request.args.get(u'objid', None)
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        order = request.args.get(u'order', u'DESC')
        field = request.args.get(u'field', u'id')
        if field not in [u'subsystem', u'type', u'id', u'objid', u'aid', 
                         u'action']:
            field = u'id'
        if field == u'subsystem':
            field = u'objtype'
        elif field == u'type':
            field = u'objdef'        
        
        if objid is not None:
            objid = objid.replace(u'_', u'//')
        objs, total = controller.objects.get(
                objtype=objtype, objdef=objdef, objid=objid, 
                page=int(page), size=int(size), order=order, field=field)

        resp = {u'objects':objs, 
                u'count':len(objs),
                u'page':page,
                u'total':total}        
        return resp

class GetObject(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):      
        obj = self.get_object(controller, oid)
        res = obj
        resp = {u'object':res} 
        return resp

class CreateObject(AuthApiView):
    """
    :param data: {
        'objects':[
        {
            'subsystem':..,
            'type':.., 
            'objid':.., 
            'desc':..        
        },..
    ]}
    """
    def dispatch(self, controller, data, *args, **kwargs):
        data = get_value(data, u'objects', None, exception=True)
        resp = controller.objects.add(data)
        return (resp, 201)

class DeleteObject(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        resp = controller.objects.remove(oid=oid)
        return (resp, 204)   

#
# object types
#
class ListObjectTypes(AuthApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        objtype = request.args.get(u'subsystem', None)
        objdef = request.args.get(u'type', None)
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        order = request.args.get(u'order', u'DESC')
        field = request.args.get(u'field', u'id')
        if field not in [u'subsystem', u'type', u'id']:
            field = u'id'
        if field == u'subsystem':
            field = u'objtype'
        elif field == u'type':
            field = u'objdef' 
            
        res, total = controller.objects.get_type(objtype=objtype, objdef=objdef, 
                                page=int(page), size=int(size), order=order, 
                                field=field)
        resp = {u'object-types':res,
                u'count':len(res),
                u'page':page,
                u'total':total} 
        return resp
    
class CreateObjectType(AuthApiView):
    """
    :param data: {
        u'object-types':[
            {
                u'subsystem':..,
                u'type':..,
            }
        ]
    }
    """
    def dispatch(self, controller, data, *args, **kwargs):
        data = get_value(data, u'object-types', None, exception=True)
        resp = controller.objects.add_types(data)
        return (resp, 201)  
    
class DeleteObjectType(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        resp = controller.objects.remove_type(oid=oid)
        return (resp, 204)      
    
#
# object action
#    
class ListObjectActions(AuthApiView):
    def dispatch(self, controller, data, *args, **kwargs):      
        res = controller.objects.get_action()
        resp = {u'object-actions':res,
                u'count':len(res)} 
        return resp    

#
# object perms
#
class ListObjectPerms(AuthApiView):
    def dispatch(self, controller, data, *args, **kwargs):      
        objtype = request.args.get(u'subsystem', None)
        objdef = request.args.get(u'type', None)
        objid = request.args.get(u'objid', None)
        user = request.args.get(u'user', None)
        role = request.args.get(u'role', None)
        group = request.args.get(u'group', None)
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        order = request.args.get(u'order', u'DESC')
        field = request.args.get(u'field', u'id')
        if field not in [u'subsystem', u'type', u'id', u'objid', u'aid', 
                         u'action']:
            field = u'id'
        if field == u'subsystem':
            field = u'objtype'
        elif field == u'type':
            field = u'objdef' 
        
        if objid is not None:
            objid = objid.replace(u'_', u'//')
            
        if user is not None:
            user = self.get_user(controller, user)
            objs, total = user.get_permissions(page=int(page), size=int(size), 
                                               order=order, field=field)
        elif role is not None:
            role = self.get_role(controller, role)
            objs, total = role.get_permissions(page=int(page), size=int(size), 
                                               order=order, field=field)            
        elif group is not None:
            group = self.get_group(controller, group)
            objs, total = group.get_permissions(page=int(page), size=int(size), 
                                               order=order, field=field)
        else:
            objs, total = controller.objects.get_permissions_with_roles(
                            objid=objid, objtype=objtype, objdef=objdef,
                            page=int(page), size=int(size), order=order, 
                            field=field)

        resp = {u'perms':objs, 
                u'count':len(objs),
                u'page':page,
                u'total':total}
        return resp  

class GetObjectPerms(AuthApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):      
        res = self.get_object_perm(controller, oid)
        resp = {u'perm':res}
        return resp

class AuthorizationAPI(ApiView):
    """Authorization API
    """
    @staticmethod
    def register_api(module):
        base = u'auth'
        rules = [
            (u'%s/users' % base, u'GET', ListUsers, {}),
            (u'%s/users/<oid>' % base, u'GET', GetUser, {}),
            #(u'%s/users/<oid>/roles' % base, u'GET', GetUserRoles, {}),
            #(u'%s/users/<oid>/perms' % base, u'GET', GetUserPerms, {}),
            #(u'%s/users/<oid>/groups' % base, u'GET', GetUserGroups, {}),
            (u'%s/users/<oid>/attributes' % base, u'GET', GetUserAtributes, {}),
            (u'%s/users' % base, u'POST', CreateUser, {}),
            (u'%s/users/<oid>' % base, u'PUT', UpdateUser, {}),
            (u'%s/users/<oid>/attributes' % base, u'POST', CreateUserAttribute, {}),
            (u'%s/users/<oid>/attributes/<aid>' % base, u'DELETE', DeleteUserAttribute, {}),
            (u'%s/users/<oid>' % base, u'DELETE', DeleteUser, {}),
            
            (u'%s/roles' % base, u'GET', ListRoles, {}),
            (u'%s/roles/<oid>' % base, u'GET', GetRole, {}),
            #(u'%s/roles/<oid>/perms' % base, u'GET', GetRolePerms, {}),
            #(u'%s/roles/<oid>/users' % base, u'GET', GetRoleUsers, {}),
            #(u'%s/roles/<oid>/groups' % base, u'GET', GetRoleGroups, {}),
            (u'%s/roles' % base, u'POST', CreateRole, {}),
            (u'%s/roles/<oid>' % base, u'PUT', UpdateRole, {}),
            (u'%s/roles/<oid>' % base, u'DELETE', DeleteRole, {}),
            
            (u'%s/groups' % base, u'GET', ListGroups, {}),
            (u'%s/groups/<oid>' % base, u'GET', GetGroup, {}),
            #(u'%s/groups/<oid>/perms' % base, u'GET', GetGroupPerms, {}),
            #(u'%s/groups/<oid>/users' % base, u'GET', GetGroupUsers, {}),
            #(u'%s/groups/<oid>/roles' % base, u'GET', GetGroupRoles, {}),
            (u'%s/groups' % base, u'POST', CreateGroup, {}),
            (u'%s/groups/<oid>' % base, u'PUT', UpdateGroup, {}),
            (u'%s/groups/<oid>' % base, u'DELETE', DeleteGroup, {}),             
         
            (u'%s/objects' % base, u'GET', ListObjects, {}),
            (u'%s/objects/<oid>' % base, u'GET', GetObject, {}),
            (u'%s/objects' % base, u'POST', CreateObject, {}),
            (u'%s/objects/<oid>' % base, u'DELETE', DeleteObject, {}),
            (u'%s/objects/types' % base, u'GET', ListObjectTypes, {}),
            (u'%s/objects/types' % base, u'POST', CreateObjectType, {}),
            (u'%s/objects/types/<oid>' % base, u'DELETE', DeleteObjectType, {}),            
            (u'%s/objects/perms' % base, u'GET', ListObjectPerms, {}),
            (u'%s/objects/perms/<oid>' % base, u'GET', GetObjectPerms, {}),
            (u'%s/objects/actions' % base, u'GET', ListObjectActions, {}),
        ]

        ApiView.register_api(module, rules)
        