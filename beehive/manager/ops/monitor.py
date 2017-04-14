'''
Created on Jan 25, 2017

@author: darkbk
'''
import ujson as json
import logging
from beecell.db.manager import RedisManager, MysqlManager
from geventhttpclient import HTTPClient
from geventhttpclient.url import URL
from pprint import PrettyPrinter
from pandas import DataFrame, set_option
from beehive.manager import ApiManager
import sys
from beecell.simple import truncate

logger = logging.getLogger(__name__)

class MonitorManager(ApiManager):
    """
    SECTION:
        monitor
    
    PARAMS:
        types list
        type get prova
        type add beehive task.ping_cloudapi 'http://localhost:8080
        type delete beehive
        
        nodes list
        node get 51
        node ping 51
        node perms 6
        node add pippo pippo beehive {\"uri\":\"dddd\"} {}
        node delete <id>    
    """
    def __init__(self, auth_config, env, frmt):
        ApiManager.__init__(self, auth_config, env, frmt)
        self.baseuri = u'/v1.0/monitor'
        self.subsystem = u'monitor'
        self.logger = logger
        self.msg = None
    
    def actions(self):
        actions = {
            u'types.list': self.get_node_types,
            u'type.get': self.get_node_type,
            u'type.add': self.add_node_type,
            u'type.delete': self.delete_node_type,
            
            u'nodes.list': self.get_nodes,
            u'node.get': self.get_node,
            u'node.ping': self.ping_node,
            u'node.perms': self.get_node_permissions,
            u'node.add': self.add_node,
            u'node.update': self.update_node,
            u'node.delete': self.delete_node,
            u'node.tags': self.get_node_tag,
            u'node.add_tag': self.add_node_tag,
            u'node.del_tag': self.remove_node_tag,
            u'node.task': self.exec_node_task,
        }
        return actions    
    
    #
    # node types
    #
    def get_node_types(self):
        uri = u'%s/node/types/' % self.baseuri
        res = self._call(uri, u'GET')
        self.logger.info(u'Get node types: %s' % truncate(res))
        self.result(res)

    def get_node_type(self, value):
        uri = u'%s/node/type/%s/' % (self.baseuri, value)
        res = self._call(uri, u'GET')
        self.logger.info(u'Get node type: %s' % truncate(res))
        self.result(res)
    
    def add_node_type(self, value, action, template):
        global oid
        data = {
            u'node_type':{
                u'value':value, 
                u'action':action, 
                u'template':template   
            }
        }
        uri = u'%s/node/type/' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(u'Add node type: %s' % truncate(res))
        self.result(res)
        
    def delete_node_type(self, value):
        uri = u'%s/node/type/%s/' % (self.baseuri, value)
        self._call(uri, u'DELETE')
        self.logger.info(u'Delete node type: %s' % value)
        self.result(True)
    
    #
    # graph
    #
    def get_graph(self):
        uri = u'%s/graph/' % self.baseuri
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)

    #
    # nodes
    #
    def get_nodes(self, tags=None):
        headers = None
        if tags is not None:
            headers = {u'tags':tags}
        uri = u'%s/nodes/' % self.baseuri
        res = self._call(uri, u'GET', headers=headers)
        self.logger.info(res)
        self.result(res)

    def get_node(self, oid):
        uri = u'%s/node/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)
        
    def ping_node(self, oid):
        uri = u'%s/node/%s/ping/' % (self.baseuri, oid)
        res = self._call(uri, u'PUT')
        self.logger.info(res)
        self.result(res)  
        
    def get_node_permissions(self, oid):
        uri = u'%s/node/%s/perms/' % (self.baseuri, oid)
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)

    def add_node(self, name, desc, ntype, conn, attribute):
        print conn
        data = {
            u'node':{
                u'name':name, 
                u'desc':desc, 
                u'type':ntype,
                u'conn':json.loads(conn),
                u'refresh':u'static',
                u'attributes':json.loads(attribute)
            }
        }
        uri = u'%s/node/' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        self.msg = u'Add node %s' % res
        self.result(res)
        
    def update_node(self, name, desc, ntype, conn, attribute):
        """TODO"""
        data = {
            u'node':{
                u'name':name, 
                u'desc':desc, 
                u'type':ntype,
                u'conn':conn,
                u'refresh':u'static',
                u'attributes':attribute
            }
        }
        uri = u'%s/node/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.result(res)
        
    def delete_node(self, oid):
        uri = u'%s/node/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'DELETE')
        self.result(res)

    def get_node_link(self):
        """TODO"""
        uri = u'%s/node/%s/links/' % (self.baseuri, oid)
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)

    def get_node_tag(self):
        """TODO"""
        global oid
        data = ''
        uri = u'%s/node/%s/tags/' % (self.baseuri, oid)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(res)
        self.result(res)
        
    def add_node_tag(self):
        """TODO"""
        global oid
        data = json.dumps({'cmd':'add', 'tag':'prova00'})
        uri = u'%s/node/%s/tag/' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(res)
        self.result(res)
        
    def remove_node_tag(self):
        """TODO"""
        global oid
        data = json.dumps({'cmd':'remove', 'tag':'prova00'})
        uri = u'%s/node/%s/tag/' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(res)
        self.result(res)

    def exec_node_task(self):
        """TODO"""
        cmd1 = u'ping -c 3 10.102.160.12'
        cmd2 = u'ps -efa|grep emperor'
        cmd3 = u'ls /etc/uwsgi/vassals'
        cmd4 = u'cat /var/run/uwsgi-emperor.pid'
        cmd5 = u'which uwsgi'
        cmd6 = u'cat /etc/uwsgi/emperor.ini'
        data = {u'task':{
                    u'name':u'tasks.run_ssh_command',
                    u'params':[cmd6, 5]
                }}
        uri = u'%s/node/%s/task/' % (self.baseuri, 386)
        res = self._call(uri, u'PUT', data=data)
        print u'out: %s' % res[u'response'][u'result'][u'stdout'].split(u'\n')
        print u'err: %s' % res[u'response'][u'result'][u'stderr']
        self.result(res)

    #
    # links
    #
    def get_links(self):
        uri = u'%s/links/' % self.baseuri
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)

    def get_link(self):
        uri = u'%s/link/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'GET')
        self.logger.info(res)
        self.result(res)
        
    def get_link_permissions(self):
        global oid
        data = ''
        uri = u'%s/link/%s/perms/' % (self.baseuri, oid)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(res)
        self.result(res)

    def add_link(self):
        data = {'name':'link1',
                'start_node':3, 
                'end_node':7,
                'attributes':{}} 
        uri = u'%s/link/' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(res)
        
    def update_link(self):
        global oid
        data = {'name':'link2',
                'start_node':3, 
                'end_node':7,
                'attributes':{'test':'bla'}}
        uri = u'%s/link/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(res)
        self.result(res)
        
    def delete_link(self):
        global oid
        data = ''
        uri = u'%s/link/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'DELETE', data=data)

    def get_link_tag(self):
        global oid
        data = ''
        uri = u'%s/link/%s/tags/' % (self.baseuri, oid)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(res)
        
    def add_link_tag(self):
        global oid
        data = json.dumps({'cmd':'add', 'tag':'prova00'})
        uri = u'%s/link/%s/tag/' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(res)
        
    def remove_link_tag(self):
        global oid
        data = json.dumps({'cmd':'remove', 'tag':'prova00'})
        uri = u'%s/link/%s/tag/' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(res)

    #
    # tags
    #
    def add_tag(self):
        data = json.dumps({'value':'prova001'})
        uri = u'%s/tag/' % self.baseuri
        res = self._call(uri, u'POST', data=data)
        self.logger.info(res)

    def count_tags(self):
        data = ''
        uri = u'%s/tags/count/' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        self.logger.info(res)
        
    def get_tags_occurrences(self):
        data = ''
        uri = u'%s/tags/occurrences/' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        self.logger.info(res)      

    def get_tags(self):
        global name
        data = ''
        uri = u'%s/tags/' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        self.logger.info(res)
        name = res[0]['value']
        
    def get_tag(self):
        global name
        data = ''
        uri = u'%s/tag/%s/' % (self.baseuri, name)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(res)

    def get_tag_perms(self):
        data = ''
        uri = u'%s/tag/%s/perms/' % (self.baseuri, 'prova00')
        res = self._call(uri, u'GET', data=data)
        self.logger.info(res)
        
    def update_tag(self):
        data = json.dumps({'value':'prova001'})
        uri = u'%s/tag/%s/' % (self.baseuri, 'prova00')
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(res)
        
        
    def delete_tag(self):
        data = ''
        uri = u'%s/tag/%s/' % (self.baseuri, 'prova001')
        res = self._call(uri, u'DELETE', data=data)      

    def gen_id(self):
        for i in range(0,13):
            print id_gen()

    #
    # keys
    #
    def get_keys(self):
        global oid
        data = ''
        uri = u'%s/keys/' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        self.logger.info(res)
        oid = res[0]['id']

    def get_key(self):
        global oid
        data = ''
        uri = u'%s/key/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(res)
        
    def get_key_permissions(self):
        global oid
        data = ''
        uri = u'%s/key/%s/perms/' % (self.baseuri, oid)
        res = self._call(uri, u'GET', data=data)
        self.logger.info(res)

    def add_key(self):
        private = '-----BEGIN RSA PRIVATE KEY-----\n'\
        'MIIEowIBAAKCAQEAqxLtlaukHh4W9NUWLOE7pkOe3qo7q424iSfP4KZWAJzO6QV5\n'\
        'q9dBvJ80WaPKaoJh518tSyJWewXej7Uj8+ttTBhsU5c0ESEvyS9FsShgPPSzkr7v\n'\
        'hNG3C3PJu9YiGVm+OzCtgOj0b0I6O4V42MJVywXIbDZVBhv52gOJ+1sM3mYCFmMN\n'\
        'C9F1GVBVUuydvhxwBl0vxPFM2tTF/Czcp+mDv9P40JrJmKBRResAj3G7xoVecvjx\n'\
        'G32Ir0WiP/YOxHfNLLoZDID/tDtoUQIxl2oMQ1dKCNL8tNtyohv1xApfQR7NvW5Y\n'\
        'P3dQuWbCLNqOXkyzPOfGLr1jm5dgCjkz+vh8DwIDAQABAoIBADS77vTWJg8Ko3Tx\n'\
        'QpavD14fNhfZTe+CDkJpPVE4tQYXUEjQYUMxZZgpU0/Wh4zxiBB0bFfey928X3DZ\n'\
        'G64TAmwUkz/pOimVm09e/RKxKYlgvQIdTWQZ6VzkYmk+huBdo6BHTxSPutmZBq5W\n'\
        'ZHwc26lrrO5+iRMLCKfFs4EB/iOHuSB1PP8qqw3LToOlhCT8EjrE57EynVg+tJHG\n'\
        'GI/n34uISFtCd410Ag8Fg1wdpdIyuQ8ZDUi8nMXlhh/5xcEjDJquThAYpudFoWXS\n'\
        'yAsC7BR7/8xMlwyUqCPEi8xziJIPc9RjIQWGPU1uLY2PxlO37WhZ0C+cOhoThyCB\n'\
        'J9W5bGECgYEA3UmS7gokBST5XabeS1IQ/Obs3yDAeJ6GuydO4jgFc7ZsmuU3u6ot\n'\
        'kzdzEEIhfYjxIVCKygBmO25rb5yvwwTEL84p52Awgi6Re1pkhhAWtRZ4m+TsWgZh\n'\
        'TCeKB4nhpqNRD8yPpqCOMxTPOdkV0OkB4SWK1UakHE3LS+X92rpsUakCgYEAxejj\n'\
        'uA3ST2GrVXVP/bDM4qA5AizKiJ+aI92GvWickvi0SZLzgUxncfXw4CMg00Pu+tY4\n'\
        'KkbJEiuCR3OakXVu9ga1l6cCKiQoliq/DMA8ams9kI9ay59ms8qsfyG15leZtkn+\n'\
        'IL767BL/QM9HSd7YzxjeQ8n1n4XJbXqTScF7YvcCgYAuwvJqnPf5olOTx8Rn1ELE\n'\
        'vqPFju09T/qWp/rScRYt2pnerZt2a8LPvkLxZ5geKAcUjCmYADeaTX4kis7Vfjdb\n'\
        'BszyGPCHQgH6OCLP9axmvgXko56Sc5CyABT5/NgTV6W0mfytMHZ8MuSLi+VBTUvZ\n'\
        'YQ6SfSgG1yWjt0lKpGRpaQKBgCqCjK9TILJ2WzP+/9CRMmEXY0dpUZOpHJXJlpCG\n'\
        'sOMM0sTe8Lj8LVgYKMYsJXfbprBwZR4HmFbzy4cHeNL3s37bEBRkBh4BKEqhIepe\n'\
        'PFvrbwznDeyg75F83jJsjkLM3DKAkDp+ay1cI0HLhBeE63MId21+Kuk59nsykgKM\n'\
        'sbEfAoGBAK0VO8gPXU4FnkZr8O1vqdvuYNrEJY+7g73aWj6vXvUgKKqCBP7tCzwA\n'\
        'buf+8e5iAHag3U61LvIhQEGi6Lw0MSaawD02iXfgsMb3XJEQgFY+fCBfAeBxLiwV\n'\
        'SF+LRB682rMLtD1cN3YG1UrTZGvNQT4V3Np1A8TmM/Y/opOV3a5Y\n'\
        '-----END RSA PRIVATE KEY-----'
        public = ''
        
        data = {u'key':
                    {u'name':u'key1',
                     u'private':private, 
                     u'public':public}}
        uri = u'%s/key/' % (self.baseuri)
        res = self._call(uri, u'POST', data=data)
        self.logger.info(res)
        
    def update_key(self):
        global oid
        data = {'name':'key2',
                'start_node':3, 
                'end_node':7,
                'attributes':{'test':'bla'}}
        uri = u'%s/key/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'PUT', data=data)
        self.logger.info(res)
        
    def delete_key(self):
        global oid
        data = ''
        uri = u'%s/key/%s/' % (self.baseuri, oid)
        res = self._call(uri, u'DELETE', data=data)
        

def monitor_main(auth_config, format, opts, args):
    """
    
    :param auth_config: {u'pwd': u'..', 
                         u'endpoint': u'http://10.102.160.240:6060/api/', 
                         u'user': u'admin@local'}
    """
    for opt, arg in opts:
        if opt in (u'-h', u'--help'):
            print __doc__
            return 0
    
    try:
        args[1]
    except:
        print __doc__
        return 0
    
    client = MonitorManager(auth_config)
    
    actions = client.actions()
    
    entity = args.pop(0)
    if len(args) > 0:
        operation = args.pop(0)
        action = u'%s.%s' % (entity, operation)
    else: 
        raise Exception(u'Monitor entity and/or command are not correct')
        return 1
    
    if action is not None and action in actions.keys():
        func = actions[action]
        res = func(*args)
    else:
        raise Exception(u'Monitor entity and/or command are not correct')
        return 1
            
    if format == u'text':
        for i in res:
            pass
    else:
        print(u'Monitor response:')
        print(u'')
        if isinstance(client.msg, dict) or isinstance(client.msg, list):
            client.pp.pprint(client.msg)
        else:
            print(client.msg)
        
    return 0

                  