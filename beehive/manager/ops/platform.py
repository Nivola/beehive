'''
Usage: manage.py [OPTION]... platform [PARAMs]...

Resource api interaction.

Mandatory arguments to long options are mandatory for short options too.
    -c, --config        json auth config file
    -f, --format        output format
    
PARAMS:
    redis ping <environment>
    mysql ping <environment> <user> <pwd> <schema>

    ansible hosts
    
    nodes list <environment>
        Get list of nodes and groups
    nodes cmd <environment> <groups> <cmd>
        Run a command <cmd> over all the server identify by <environment> and
        <groups>
    beehive nodes <environment> <subsystem>
    beehive instances <environment> <subsystem> [details]
    beehive blacklist <environment> <subsystem>
    
    beehive syncdev <environment> <subsystem> <instance>
    beehive deploy <environment> <subsystem> <instance>
    beehive undeploy <environment> <subsystem> <instance>
    
    portal syncdev <environment> <client> <instance>
    portal deploy <environment> <client> <instance>
    portal undeploy <environment> <client> <instance>

Exit status:
 0  if OK,
 1  if problems occurred

Created on Jan 9, 2017

@author: darkbk
'''
import logging
import ujson as json
import yaml
from beecell.db.manager import RedisManager, MysqlManager
from geventhttpclient import HTTPClient
from geventhttpclient.url import URL
from pprint import PrettyPrinter
from beehive.manager.util.ansible2 import Options, Runner
from beehive.manager.manage.config import host
from passlib import hosts


logger = logging.getLogger(__name__)

class PlatformManager(object):
    def __init__(self, auth_config, frmt=u'json'):
        self.baseuri = u'/v1.0/resource'
        self.subsystem = u'resource'
        self.logger = logger
        self.json = None
        self.text = []
        self.pp = PrettyPrinter(width=200)
        self.ansible_path = auth_config[u'ansible_path']
        self.verbosity = 3
        self.format = frmt
        self.playbook = u'%s/site.yml' % (self.ansible_path)
        self.local_package_path = auth_config[u'local_package_path']
    
    def actions(self):
        actions = {
            u'redis.ping': self.redis_ping,
            u'mysql.ping': self.mysql_ping,

            u'ansible.play': self.ansible_playbook,
            u'ansible.task': self.ansible_task,
            
            u'nodes.list': self.ansible_inventory,
            u'nodes.cmd': self.nodes_run_cmd,
            
            u'beehive.nodes': self.beehive_nodes_stats,
            u'beehive.instances': self.beehive_nodes_vassals,
            u'beehive.blacklist': self.beehive_nodes_blacklist,
            u'beehive.syncdev':self.beehive_syncdev,
            u'beehive.deploy':self.beehive_deploy,
            u'beehive.undeploy':self.beehive_undeploy,
            u'beehive.ping':self.beehive_ping,
            u'beehive.tree':self.beehive_get_uwsgi_tree,
            
            u'portal.nodes': self.portal_nodes_stats,
            u'portal.instances': self.portal_nodes_vassals,
            u'portal.blacklist': self.portal_nodes_blacklist,            
            u'portal.syncdev':self.portal_syncdev,
            u'portal.deploy':self.portal_deploy,
            u'portal.undeploy':self.portal_undeploy,
            u'portal.tree':self.portal_get_uwsgi_tree,
        }
        return actions    
    
    #
    # ansible
    #
    def ansible_inventory(self, environment):
        """list host by section
        """
        path_inventory = u'%s/inventories/%s' % (self.ansible_path, environment)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
        hosts = runner.get_inventory()
        if self.format == u'json':
            self.json = hosts
        elif self.format == u'text':
            for k,v in hosts.items():
                self.text.append(u'%-30s %s' % (k, (u', ').join(v)))
        
    
    # gather info by section and host
    # test by section and host
    # get specific info from beehive section
    
    def ansible_playbook(self, environment, section, run_data):
        """run playbook on section and host
        """
        path_inventory = u'%s/inventories/%s' % (self.ansible_path, environment)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
        tags = run_data.pop(u'tags')
        runner.run_playbook(section, self.playbook, None, run_data, None, 
                            tags=tags)

    def ansible_task(self, environment, section):
        """Run ansible tasks over a group of hosts
        
        :param environment: platform environment. Ex. test, dev, prod
        :parma section: ansible host group
        """
        path_inventory = u'%s/inventories/%s' % (self.ansible_path, environment)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
        tasks = [
            dict(action=dict(module='shell', args='ls'), register='shell_out'),
        ]
        runner.run_task(section, tasks=tasks, frmt=self.format)

    #
    # platform node
    #
    def nodes_run_cmd(self, environment, section, cmd):
        """Run ansible tasks over a group of hosts
        
        :param environment: platform environment. Ex. test, dev, prod
        :parma section: ansible host group
        """
        path_inventory = u'%s/inventories/%s' % (self.ansible_path, environment)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
        tasks = [
            dict(action=dict(module=u'shell', args=cmd), register=u'shell_out'),
        ]
        runner.run_task(section, tasks=tasks, frmt=self.format)

    #
    # beehive
    #
    def beehive_syncdev(self, environment, subsystem, vassal):
        """Sync beehive server package in developer mode
        """
        run_data = {
            u'local_package_path':self.local_package_path,
            u'subsystem':subsystem,
            u'vassal':u'%s-%s' % (subsystem, vassal),
            u'tags':[u'sync-dev']
        }        
        self.ansible_playbook(environment, u'beehive', run_data)
           
    def beehive_deploy(self, environment, subsystem, vassal):
        """Deploy beehive instance for subsystem
        """
        run_data = {
            u'subsystem':subsystem,
            u'vassal':u'%s-%s' % (subsystem, vassal),
            u'tags':[u'deploy']
        }        
        self.ansible_playbook(environment, u'beehive', run_data)
    
    def beehive_undeploy(self, environment, subsystem, vassal):
        """Deploy beehive instance for subsystem
        """
        run_data = {
            u'subsystem':subsystem,
            u'vassal':u'%s-%s' % (subsystem, vassal),
            u'tags':[u'undeploy']
        }        
        self.ansible_playbook(environment, u'beehive', run_data)
        
    def beehive_nodes_stats(self, environment):
        self.get_emperor_nodes_stats(environment, u'beehive')
        
    def beehive_nodes_blacklist(self, environment, details=u''):
        self.get_emperor_blacklist(environment, details, u'beehive')
        
    def beehive_nodes_vassals(self, environment, details=u''):
        self.get_emperor_vassals(environment, details, u'beehive')
        
    def beehive_ping(self, environment):
        """Ping beehive instance
        
        :param server: host name
        :param port: server port [default=6379]
        """
        path_inventory = u'%s/inventories/%s' % (self.ansible_path, environment)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
        hosts, vars = runner.get_inventory_with_vars(u'beehive')
        print hosts
        print vars
        
        url = URL(u'http://%s:%s/v1.0/server/ping/' % (server, port))
        http = HTTPClient(url.host, port=url.port)
        # issue a get request
        response = http.get(url.request_uri)
        # read status_code
        response.status_code
        # read response body
        res = json.loads(response.read())
        # close connections
        http.close()
        if res[u'status'] == u'ok':
            resp = True
        else:
            resp = False
        self.logger.info(u'Ping beehive %s : %s' % (url.request_uri, resp))
        self.json = u'Ping beehive %s : %s' % (url.request_uri, resp)
        
    def beehive_get_uwsgi_tree(self, environment):
        """
        """
        self.__get_uwsgi_tree(environment, u'beehive')
        
    #
    # portal
    #    
    def portal_syncdev(self, environment, subsystem, vassal):
        """Sync beehive server package in developer mode
        """
        run_data = {
            u'local_package_path':self.local_package_path,
            u'client':subsystem,
            u'vassal':u'%s-%s' % (subsystem, vassal),
            u'tags':[u'sync-dev']
        }        
        self.ansible_playbook(environment, u'beehive-portal', run_data)
           
    def portal_deploy(self, environment, subsystem, vassal):
        """Deploy beehive instance for subsystem
        """
        run_data = {
            u'client':subsystem,
            u'vassal':u'%s-%s' % (subsystem, vassal),
            u'tags':[u'deploy']
        }        
        self.ansible_playbook(environment, u'beehive-portal', run_data)
    
    def portal_undeploy(self, environment, subsystem, vassal):
        """Deploy beehive instance for subsystem
        """
        run_data = {
            u'client':subsystem,
            u'vassal':u'%s-%s' % (subsystem, vassal),
            u'tags':[u'undeploy']
        }        
        self.ansible_playbook(environment, u'beehive-portal', run_data)
    
    def portal_nodes_stats(self, environment):
        self.get_emperor_nodes_stats(environment, u'beehive-portal')
        
    def portal_nodes_blacklist(self, environment, details=u''):
        self.get_emperor_blacklist(environment, details, u'beehive-portal')
        
    def portal_nodes_vassals(self, environment, details=u''):
        self.get_emperor_vassals(environment, details, u'beehive-portal')    
    
    def portal_get_uwsgi_tree(self, environment):
        """
        """
        self.__get_uwsgi_tree(environment, u'beehive-portal')    
    
    #
    # test
    #
    def redis_ping(self, environment):
        """Test redis instance
        
        :param server: host name
        :param port: server port [default=6379]
        """
        path_inventory = u'%s/inventories/%s' % (self.ansible_path, environment)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
        hosts, vars = runner.get_inventory_with_vars(u'redis')        
        
        for host in hosts:
            redis_uri = u'%s;%s;1' % (host, 6379)
            server = RedisManager(redis_uri)
            res = server.ping()
            self.logger.info(u'Ping redis %s : %s' % (redis_uri, res))

            self.json = []
            if self.format == u'json':
                self.json.append({u'host':host, u'response':res})
            elif self.format == u'text':
                self.text.append(u'%s: %s' % (host, res))
            
    def mysql_ping(self, environment, user, pwd, db, port=3306):
        """Test redis instance
        
        :param server: host name
        :param port: server port [default=6379]
        """
        path_inventory = u'%s/inventories/%s' % (self.ansible_path, environment)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
        hosts, vars = runner.get_inventory_with_vars(u'mysql')        
        
        for host in hosts:
            db_uri = u'mysql+pymysql://%s:%s@%s:%s/%s' % (user, pwd, host, port, db)
            server = MysqlManager(1, db_uri)
            server.create_simple_engine()
            res = server.ping()
            self.logger.info(u'Ping mysql %s : %s' % (db_uri, res))

            self.json = []
            if self.format == u'json':
                self.json.append({u'host':host, u'response':res})
            elif self.format == u'text':
                self.text.append(u'%s: %s' % (host, res))
    
    def test_beehive(self, server, port):
        """Test redis instance
        
        :param server: host name
        :param port: server port [default=6379]
        """
        url = URL(u'http://%s:%s/v1.0/server/ping/' % (server, port))
        http = HTTPClient(url.host, port=url.port)
        # issue a get request
        response = http.get(url.request_uri)
        # read status_code
        response.status_code
        # read response body
        res = json.loads(response.read())
        # close connections
        http.close()
        if res[u'status'] == u'ok':
            resp = True
        else:
            resp = False
        self.logger.info(u'Ping beehive %s : %s' % (url.request_uri, resp))
        self.json = u'Ping beehive %s : %s' % (url.request_uri, resp)
        
    #
    # uwsgi emperor
    #
    def __get_stats(self, server):
        import socket
        err = 104
        while err == 104:
            try:
                import httplib
                conn = httplib.HTTPConnection(server, 80, timeout=1)
                conn.request(u'GET', u'/', None, {})
                response = conn.getresponse()
                res = response.read()
                conn.close()
                err = 0     
            except socket.error as ex:
                err = ex[0]
                
        if response.status == 200:
            res = json.loads(res)
            self.logger.info(res)
        else:
            self.logger.error(u'Emperor %s does not respond' % server)
            res = u'Emperor %s does not respond' % server
        return res

    def __get_uwsgi_tree(self, environment, section):
        """
        """
        '''path_inventory = u'%s/inventories/%s' % (self.ansible_path, environment)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
        hosts = runner.get_inventory(section=section)
        self.json = []
        cmd = []
        for host in hosts:
            res = self.__get_stats(host)
            pid = res[u'pid']
            cmd.append(u'pstree -ap %s' % pid)'''

        self.nodes_run_cmd(environment, section, u'pstree -ap')

    def get_emperor_nodes_stats(self, environment, system):
        """Get uwsgi emperor statistics
        
        :param server: host name
        """
        path_inventory = u'%s/inventories/%s' % (self.ansible_path, environment)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
        hosts = runner.get_inventory(section=system)
        self.json = []
        for host in hosts:
            res = self.__get_stats(host)
            res.pop(u'vassals')
            res.pop(u'blacklist')            
            if self.format == u'json':
                self.json.append(res)
            elif self.format == u'text':
                self.text.append(u'%s' % (host))
                for k,v in res.items():
                    self.text.append(u'- %-15s : %s' % (k,v))

    def get_emperor_vassals(self, environment, details=u'', system=None):
        """Get uwsgi emperor active vassals statistics
        
        :param server: host name
        """
        path_inventory = u'%s/inventories/%s' % (self.ansible_path, environment)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
        hosts = runner.get_inventory(section=system)
        self.json = []
        for host in hosts:
            res = self.__get_stats(host)
            vassals = res.pop(u'vassals')         
            if self.format == u'json':
                self.json.append(vassals)
            elif self.format == u'text':
                self.text.append(u'\n%s' % (host))
                for inst in vassals:
                    self.text.append(u'- %s' % (inst.pop(u'id')\
                                                .replace(u'.ini', u'')\
                                                .replace(u'/etc/uwsgi/vassals/', u'')))
                    if details == u'details':
                        for k,v in inst.items():
                            self.text.append(u'  - %-15s : %s' % (k,v))
                    else:
                        for k in [u'pid', u'ready', u'accepting']:
                            self.text.append(u'  - %-15s : %s' % (k, inst[k]))
                            
    def get_emperor_blacklist(self, environment, details=u'', system=None):
        """Get uwsgi emperor active vassals statistics
        
        :param server: host name
        """
        path_inventory = u'%s/inventories/%s' % (self.ansible_path, environment)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
        hosts = runner.get_inventory(section=system)
        self.json = []
        for host in hosts:
            res = self.__get_stats(host)
            blacklist = res.pop(u'blacklist')          
            if self.format == u'json':
                self.json.append(blacklist)
            elif self.format == u'text':
                self.text.append(u'\n%s' % (host))
                for inst in blacklist:
                    self.text.append(u'- %s' % (inst.pop(u'id')\
                                                .replace(u'.ini', u'')\
                                                .replace(u'/etc/uwsgi/vassals/', u'')))
                    for k,v in inst.items():
                        self.text.append(u'  - %-15s : %s' % (k,v))                          
    
def platform_main(auth_config, frmt, opts, args):
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
    
    client = PlatformManager(auth_config, frmt=frmt)
    actions = client.actions()
    
    entity = args.pop(0)
    if len(args) > 0:
        operation = args.pop(0)
        action = u'%s.%s' % (entity, operation)
    else: 
        raise Exception(u'Platform entity and/or command are not correct')
        return 1
    
    #print(u'platform %s %s response:' % (entity, operation))
    #print(u'---------------------------------------------------------------')
    print(u'')
    
    if action is not None and action in actions.keys():
        func = actions[action]
        res = func(*args)
    else:
        raise Exception(u'Platform entity and/or command are not correct')
        return 1

    if frmt == u'text':
        if len(client.text) > 0:
            print(u'\n'.join(client.text))
    else:
        if client.json is not None:
            if isinstance(client.json, dict) or isinstance(client.json, list):
                client.pp.pprint(client.json)
            else:
                print(client.json)
        
    return 0    