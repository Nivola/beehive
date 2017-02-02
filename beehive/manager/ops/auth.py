'''
Created on Jan 9, 2017

@author: darkbk
'''
import logging
from beecell.db.manager import RedisManager, MysqlManager
from geventhttpclient import HTTPClient
from geventhttpclient.url import URL
from pprint import PrettyPrinter
from pandas import DataFrame, set_option
from beehive.common.apiclient import BeehiveApiClient

logger = logging.getLogger(__name__)

def auth_main(auth_config, format, args):
    """
    
    :param auth_config: {u'pwd': u'..', 
                         u'endpoint': u'http://10.102.160.240:6060/api/', 
                         u'user': u'admin@local'}
    """
    try:
        entity = args.pop(0)
    except Exception as ex:
        entity = u'ping'

    pp = PrettyPrinter(width=200)
    
    client = BeehiveApiClient(auth_config[u'endpoint'], 
                              auth_config[u'user'], 
                              auth_config[u'pwd'],
                              auth_config[u'catalog'])
    
    if (entity == u'ping'):
        try:
            service = args.pop(0)
        except:
            service = u'auth'
        res = client.ping(service)
        if format == u'text':
            for i in res:
                print(u'Ping %s://%s:%s : %s' % (i[0][u'proto'],
                                                 i[0][u'host'],
                                                 i[0][u'port'],
                                                 i[1]))
        else:
            print(u'Ping :')
            pp.pprint(res)
    
    elif (entity == u'services'):
        res = client.endpoints
        if format == u'text':
            for service, endpoints in res.items():
                print(u'Service [%s] endpoints: ' % service)
                for i in endpoints:
                    
                    print(u'- %s://%s:%s' % (i[u'proto'],
                                             i[u'host'],
                                             i[u'port']))
        else:
            print(u'Services :')
            pp.pprint(res)
            
    elif (entity == u'catalog'):
        try:
            cmd = args.pop(0)
        except:
            cmd = u'list'
        if cmd == u'list':    
            res = client.get_catalogs()

            if format == u'text':
                pass
            else:
                print(u'Catalogs :')
                pp.pprint(res)
        
        elif cmd == u'get':
            try:
                catalog_id = args.pop(0)
            except:
                print(u'ERROR : Specify catalog id')
                return 1
            
            res = client.get_catalog(catalog_id)
            
            if format == u'text':
                pass
            else:
                print(u'Catalog :')
                pp.pprint(res)
                
        elif cmd == u'add':
            try:
                name = args.pop(0)
                zone = args[4]
            except:
                print(u'ERROR : Specify catalog name and zone')
                return 1
            
            res = client.create_catalog(name, zone)
            
            if format == u'text':
                pass
            else:
                print(u'Add catalog %s with id : %s' % (name, res))
                
        elif cmd == u'delete':
            try:
                catalog_id = args.pop(0)
            except:
                print(u'ERROR : Specify catalog id')
                return 1
            
            res = client.delete_catalog(catalog_id)
            
            if format == u'text':
                pass
            else:
                print(u'Delete catalog %s' % (catalog_id))
                
    elif (entity == u'endpoint'):
        try:
            cmd = args.pop(0)
        except:
            cmd = u'list'
            
        if cmd == u'list':    
            res = client.get_endpoints()

            if format == u'text':
                pass
            else:
                print(u'Endpoints :')
                pp.pprint(res)            
            
        if cmd == u'get':
            try:
                endpoint_id = args.pop(0)
            except:
                print(u'ERROR : Specify endpoint id')
                return 1
            
            res = client.get_endpoint(endpoint_id)
            
            if format == u'text':
                pass
            else:
                print(u'Endpoint :')
                pp.pprint(res) 
                
        elif cmd == u'add':
            try:
                name = args.pop(0)
                catalog = args[4]
                service = args[5]
                uri = args[6]
            except:
                print(u'ERROR : Specify endpoint name, catalog, service and uri')
                return 1
            
            # if endpoint exist update it else create new one
            try:
                res = client.get_endpoint(name)
                res = client.update_endpoint(name, catalog_id=catalog, 
                                             name=name, 
                                             service=service, uri=uri)
            except Exception as ex:
                logger.error(ex, exc_info=1)
                res = client.create_endpoint(catalog, name, service, uri)
            
            if format == u'text':
                pass
            else:
                print(u'Add endpoint %s with id : %s' % (name, res))
                
        elif cmd == u'delete':
            try:
                endpoint_id = args.pop(0)
            except:
                print(u'ERROR : Specify endpoint id/name')
                return 1
            
            res = client.delete_endpoint(endpoint_id)
            
            if format == u'text':
                pass
            else:
                print(u'Delete endpoint %s' % (endpoint_id))                
    
    elif (entity == u'perm'):
        try:
            cmd = args.pop(0)
        except:
            cmd = u'list'
            
        if cmd == u'list':            
            get_all_permissions(client, pp, format)
            
    elif (entity == u'object'):
        try:
            cmd = args.pop(0)
        except:
            cmd = u'list'
            
        if cmd == u'list':            
            get_all_objects(client, pp, format)
            
    elif (entity == u'user'):
        try:
            cmd = args.pop(0)
        except:
            cmd = u'list'
            
        if cmd == u'list':            
            get_users(client, pp, format)
        elif cmd == u'get':
            try:
                oid = args.pop(0)
            except:
                print(u'ERROR : Specify user name')
                return 1
            get_user(client, pp, format, oid)
        elif cmd == u'add_system':
            try:
                name = args.pop(0)
                password = args[4]
                description = args[5]
            except:
                print(u'ERROR : Specify user name, description, password')
                return 1
            
            res = client.add_system_user(name, password, description)
            
            if format == u'text':
                print(u'Add user %s with id : %s' % (name, res))
            else:
                pass
        elif cmd == u'delete':
            try:
                oid = args.pop(0)
            except:
                print(u'ERROR : Specify user name')
                return 1
            
            client.remove_user(oid)
            
            if format == u'text':
                print(u'Remove user %s' % (oid))
            else:
                pass
    
    elif (entity == u'role'):
        try:
            cmd = args.pop(0)
        except:
            cmd = u'list'
            
        if cmd == u'list':            
            get_roles(client, pp, format)
        elif cmd == u'get':
            try:
                oid = args.pop(0)
            except:
                print(u'ERROR : Specify role name')
                return 1
            get_role(client, pp, format, oid)
    
    client.logout()
    return 0          

def get_all_permissions(client, pp, format):       
    data = u''
    uri = u'/api/auth/object/perm/'
    res = client.invoke(u'auth', uri, u'GET', data)
    set_option(u'display.width', 200)
    df =  DataFrame(res)
    print u'----- PERMS LIST -----'
    print(df)
    print

def get_all_objects(client, pp, format):
    data = u''
    uri = u'/api/auth/object/'
    res = client.invoke(u'auth', uri, u'GET', data)
    set_option(u'display.width', 200)
    set_option(u'display.height', 200)
    df =  DataFrame(res)
    print '----- PERMS LIST -----'
    print(df)
    print

def get_users(client, pp, format):
    data = u''
    uri = u'/api/auth/user/'
    res = client.invoke(u'auth', uri, u'GET', data)
    
    if format == u'text':
        print(u'%-5s%-60s%-60s%5s' % (u'id', u'name', u'desc', u'active'))
        print(u'')
        for i in res:
            print(u'%-5s%-60s%-60s%5s' % (i[u'id'], i[u'name'], i[u'desc'], i[u'active']))
    else:
        print(u'Users :')
        pp.pprint(res)

def get_user(client, pp, format, name):
    data = u''
    uri = u'/api/auth/user/%s/' % name
    res = client.invoke(u'auth', uri, u'GET', data)

    if format == u'text':
        print u'----- USER INFO -----'
        print u'%-12s: %s' % (u'id', res[u'id'])
        print u'%-12s: %s' % (u'name', res[u'name']) 
        print u'%-12s: %s' % (u'description', res[u'desc'])
        print u'%-12s: %s' % (u'attribute', res[u'attribute'])
        print u'%-12s: %s' % (u'type', res[u'type'])
        print u'%-12s: %s' % (u'created_date', res[u'date'][u'creation'])
        print u'%-12s: %s' % (u'modified_date', res[u'date'][u'modified'])
        print u'%-12s:' % (u'roles')
        print u'  %-20s %-30s' % (u'name', u'description')
        print u'  -----------------------------------------------------------------------------------------------------'
        for role in res[u'roles']:
            print u'  %-20s %-30s' % (role[1], role[2])
        print
        print u'%-12s:' % (u'perms')
        print u'  %-12s %-30s %-50s %-8s' % (u'type', u'definition', u'value', u'action')
        print u'  -----------------------------------------------------------------------------------------------------'
        for perm in res[u'perms']:
            print u'  %-12s %-80s %-80s %-8s' % (perm[2], perm[3], perm[5], perm[7])
        print
    else:
        print(u'User :')
        pp.pprint(res)    

def get_roles(client, pp, format):
    data = u''
    uri = u'/api/auth/role/'
    res = client.invoke(u'auth', uri, u'GET', data)
    
    if format == u'text':
        print(u'%-5s%-60s%-60s%5s' % (u'id', u'name', u'desc', u'active'))
        print(u'')
        for i in res:
            print(u'%-5s%-60s%-60s%5s' % (i[u'id'], i[u'name'], i[u'desc'], i[u'active']))
    else:
        print(u'Roles :')
        pp.pprint(res)

def get_role(client, pp, format, oid):
    uri = u'/api/auth/role/%s/' % oid
    res = client.invoke(u'auth', uri, u'GET', u'')
    uri = u'/api/auth/role/%s/perm/' % oid
    perms = client.invoke(u'auth', uri, u'GET', u'')    

    if format == u'text':
        print u'----- ROLE INFO -----'
        print u'%-12s: %s' % (u'id', res[u'id'])
        print u'%-12s: %s' % (u'name', res[u'name']) 
        print u'%-12s: %s' % (u'description', res[u'desc'])
        print u'%-12s:' % (u'perms')
        print u'  %-12s %-30s %-50s %-8s' % (u'type', u'definition', u'value', u'action')
        print u'  -----------------------------------------------------------------------------------------------------'
        for perm in perms:
            print u'  %-12s %-30s %-50s %-8s' % (perm[2], perm[3], perm[5], perm[7])
        print
    else:
        print(u'Role :')
        pp.pprint(res)
        print(u'Role perms:')
        pp.pprint(perms)        

def remove_obj(client, objid):
    data = u''
    uri = u'/api/auth/object/%s/' % objid
    res = client.invoke(u'auth', uri, u'DELETE', data)
    