'''
Created on Sep 22, 2017

@author: darkbk
'''
import ujson as json
import gevent
from datetime import datetime
from httplib import HTTPConnection
from beecell.simple import str2uni
from beehive.manager.util.controller import BaseController
from beecell.db.manager import RedisManager, MysqlManager
from cement.core.controller import expose
from geventhttpclient import HTTPClient
from geventhttpclient.url import URL
from logging import getLogger
try:
    from beehive.manager.util.ansible2 import Options, Runner
except Exception as ex:
    print(u'ansible package not installed. %s' % ex)  

logger = getLogger(__name__)

class AnsibleController(BaseController):
    class Meta:
        stacked_on = 'platform'
        stacked_type = 'nested'

    def _setup(self, base_app):
        BaseController._setup(self, base_app)

        self.baseuri = u'/v1.0/resource'
        self.subsystem = u'resource'
        self.ansible_path = self.configs[u'ansible_path']
        self.verbosity = 2
        self.main_playbook= u'%s/site.yml' % (self.ansible_path)
        self.beehive_playbook= u'%s/beehive.yml' % (self.ansible_path)
        self.beehive_doc_playbook= u'%s/beehive-doc.yml' % (self.ansible_path)
        self.local_package_path = self.configs[u'local_package_path']
    
    #
    # ansible
    #
    def ansible_inventory(self):
        """list host by group
        """
        try:
            path_inventory = u'%s/inventories/%s' % (self.ansible_path, self.env)
            path_lib = u'%s/library/beehive/' % (self.ansible_path)
            runner = Runner(inventory=path_inventory, verbosity=self.verbosity, 
                            module=path_lib)
            res = runner.get_inventory()
            resp = []
            for k,v in res.items():
                resp.append({u'group':k, u'hosts':u', '.join(v)})
            logger.debug(u'Ansible inventory nodes: %s' % res)
            self.result(resp, headers=[u'group', u'hosts'], maxsize=400)
        except Exception as ex:
            self.error(ex)
    
    def ansible_playbook(self, group, run_data, playbook=None):
        """run playbook on group and host
        """
        try:
            path_inventory = u'%s/inventories/%s' % (self.ansible_path, self.env)
            path_lib = u'%s/library/beehive/' % (self.ansible_path)
            runner = Runner(inventory=path_inventory, verbosity=self.verbosity, 
                            module=path_lib)
            tags = run_data.pop(u'tags')
            if playbook is None:
                playbook = self.playbook
            runner.run_playbook(group, playbook, None, run_data, None, 
                                tags=tags)
        except Exception as ex:
            self.error(ex)
    
    def ansible_task(self, group):
        """Run ansible tasks over a group of hosts
        
        :parma group: ansible host group
        """
        try:
            path_inventory = u'%s/inventories/%s' % (self.ansible_path, self.env)
            path_lib = u'%s/library/beehive/' % (self.ansible_path)
            runner = Runner(inventory=path_inventory, verbosity=self.verbosity, 
                            module=path_lib)
            tasks = [
                dict(action=dict(module='shell', args='ls'), register='shell_out'),
            ]
            runner.run_task(group, tasks=tasks, frmt=self.format)
        except Exception as ex:
            self.error(ex)            

class PlatformController(BaseController):
    class Meta:
        label = 'platform'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Platform management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)

    @expose(help="Platform management", hide=True)
    def default(self):
        self.app.args.print_help()

class RedisController(AnsibleController):
    class Meta:
        label = 'redis'
        description = "Redis management"
        
    @expose(help="Redis management", hide=True)
    def default(self):
        self.app.args.print_help()
        
    def __run_cmd(self, func, dbs=[0]):
        """Run command on redis instances
        """
        try:
            path_inventory = u'%s/inventories/%s' % (self.ansible_path, self.env)
            path_lib = u'%s/library/beehive/' % (self.ansible_path)
            runner = Runner(inventory=path_inventory, verbosity=self.verbosity, 
                            module=path_lib)
            hosts, vars = runner.get_inventory_with_vars(u'redis')        
            
            resp = []
            for host in hosts:
                for db in dbs:
                    uri = u'%s;%s;%s' % (host, 6379, db)
                    server = RedisManager(uri)
                    res = func(server)
                    #res = server.ping()
                    
                    if isinstance(res, dict):
                        for k,v in res.items():
                            resp.append({u'host':str(host), u'db':db, 
                                         u'response':u'%s = %s' % (k,v)})
                    elif isinstance(res, list):
                        for v in res:
                            resp.append({u'host':str(host), u'db':db, 
                                         u'response':v})                        
                    else:
                        resp.append({u'host':str(host), u'db':db, u'response':res})
                logger.info(u'Ping redis %s : %s' % (uri, resp))
            self.result(resp, headers=[u'host', u'db', u'response'])
        except Exception as ex:
            self.error(ex)            
        
    @expose()
    def ping(self):
        """Ping redis instances
        """        
        def func(server):
            return server.ping()
        self.__run_cmd(func)
    
    @expose()
    def info(self):
        """Info from redis instances
        """        
        def func(server):
            return server.info()
        self.__run_cmd(func)
    
    @expose()
    def config(self):
        """Config of redis instances
        """        
        def func(server):
            return server.config()
        self.__run_cmd(func) 
    
    @expose()
    def size(self):
        """Size of redis instances
        """
        def func(server):
            return server.size()
        self.__run_cmd(func, dbs=range(0,8))
    
    @expose()
    def client_list(self):
        """Client list of redis instances
        """        
        def func(server):
            return server.server.client_list()
        self.__run_cmd(func)         
    
    @expose()
    def flush(self):
        """Flush redis instances
        """        
        def func(server):
            return server.server.flushall()
        self.__run_cmd(func)  
    
    @expose(aliases=[u'inspect [pattern]'], aliases_only=True)
    def inspect(self):
        """Inspect redis instances
    - pattern: keys search pattern [default=*]
        """        
        pattern = self.get_arg(default=u'*')
        
        def func(server): 
            return server.inspect(pattern=pattern, debug=False)
        self.__run_cmd(func, dbs=range(0,8))
    
    @expose(aliases=[u'query [pattern]'], aliases_only=True)
    def query(self):
        """Query redis instances by key
    - pattern: keys search pattern [default=*]
        """        
        pattern = self.get_arg(default=u'*')
        count = self.get_arg(default=False)      

        def func(server):
            keys = server.inspect(pattern=pattern, debug=False)
            res = server.query(keys, ttl=False)
            if count:
                resp = []
                for k,v in res.items():
                    resp.append({k:len(v)})
                return resp
            return res
        self.__run_cmd(func, dbs=range(0,8))
    
    @expose(aliases=[u'delete [pattern]'], aliases_only=True)
    def delete(self):
        """Delete redis instances keys.
    - pattern: keys search pattern [default=*]
        """        
        pattern = self.get_arg(default=u'*')
        
        def func(server):
            return server.delete(pattern=pattern)
        self.__run_cmd(func, dbs=range(0,8))
        
class MysqlController(AnsibleController):
    class Meta:
        label = 'mysql'
        description = "Mysql management"
        
    @expose(help="Mysql management", hide=True)
    def default(self):
        self.app.args.print_help()
    
    @expose(aliases=[u'ping user pwd db [port]'], aliases_only=True)
    def ping(self):
        """Test mysql instance
    - user: user
    - pwd: user password
    - db: db schema
    - port: instance port [default=3306]
        """
        user = self.get_arg(name=u'user')
        pwd  = self.get_arg(name=u'pwd')
        db  = self.get_arg(name=u'db')
        port = self.get_arg(default=3306)
        
        path_inventory = u'%s/inventories/%s' % (self.ansible_path, self.env)
        path_lib = u'%s/library/beehive/' % (self.ansible_path)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity, 
                        module=path_lib)
        hosts, vars = runner.get_inventory_with_vars(u'mysql')        
        resp = []
        for host in hosts:
            db_uri = u'mysql+pymysql://%s:%s@%s:%s/%s' % (user, pwd, host, port, db)
            server = MysqlManager(1, db_uri)
            server.create_simple_engine()
            res = server.ping()
            resp.append({u'host':host, u'response':res})
            logger.info(u'Ping mysql %s : %s' % (db_uri, res))
        
        self.result(resp, headers=[u'host', u'response'])        

class NodeController(AnsibleController):
    class Meta:
        label = 'node'
        description = "Nodes management"
        
    @expose(help="Nodes management", hide=True)
    def default(self):
        self.app.args.print_help()
        
    @expose()
    def list(self):
        """List managed platform nodes
        """
        self.ansible_inventory()        
        
    @expose(aliases=[u'cmd <group> <cmd>'], aliases_only=True)
    def cmd(self):
        """Execute command on managed platform nodes
    - group: ansible group
    - cmd: shell command   
        """
        group = self.get_arg(name=u'group')
        cmd  = self.get_arg(name=u'cmd')     
        path_inventory = u'%s/inventories/%s' % (self.ansible_path, self.env)
        path_lib = u'%s/library/beehive/' % (self.ansible_path)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity, 
                        module=path_lib)
        tasks = [
            dict(action=dict(module=u'shell', args=cmd), register=u'shell_out'),
        ]
        runner.run_task(group, tasks=tasks, frmt=u'text')
        
class BeehiveController(AnsibleController):
    class Meta:
        label = 'beehive'
        description = "Beehive management"
    
    #
    # uwsgi
    #
    def __get_stats(self, server):
        import socket
        err = 104
        while err == 104:
            try:
                conn = HTTPConnection(server, 81, timeout=1)
                conn.request(u'GET', u'/', None, {})
                response = conn.getresponse()
                res = response.read()
                conn.close()
                err = 0
                logger.debug(u'Connect %s uwsgi stats' % (server))
            except socket.error as ex:
                err = ex[0]
                
        if response.status == 200:
            try:
                res = json.loads(res)
                logger.info(res)
            except:
                res = {u'vassals':None, u'blacklist':None}
        else:
            logger.error(u'Emperor %s does not respond' % server)
            res = u'Emperor %s does not respond' % server
        return res

    def __get_uwsgi_tree(self, group):
        """
        """
        '''path_inventory = u'%s/inventories/%s' % (self.ansible_path, self.env)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
        hosts = runner.get_inventory(group=group)
        self.json = []
        cmd = []
        for host in hosts:
            res = self.__get_stats(host)
            pid = res[u'pid']
            cmd.append(u'pstree -ap %s' % pid)'''

        self.nodes_run_cmd(self.env, group, u'pstree -ap')

    def get_emperor_nodes_stats(self, system):
        """Get uwsgi emperor statistics
        
        :param server: host name
        """
        path_inventory = u'%s/inventories/%s' % (self.ansible_path, self.env)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
        hosts = runner.get_inventory(group=system)
        self.json = []
        resp = []
        for host in hosts:
            res = self.__get_stats(host)
            vassals = res.pop(u'vassals')
            res.pop(u'blacklist')
            try:
                temp = [u'%s [%s]' % (v[u'id']\
                                  .replace(u'/etc/uwsgi/vassals/', u'')\
                                  .replace(u'.ini', u'')\
                                  , v[u'pid']) for v in vassals]
                res[u'vassals'] = u', '.join(temp)
            except:
                res[u'vassals'] = []
            res[u'host'] = host
            resp.append(res)
        self.result(resp, headers=[u'host', u'pid', u'version', u'uid', u'gid', 
                                   u'throttle_level', u'emperor_tyrant', 
                                   u'vassals'], maxsize=300)

    def cdate(self, date):
        """
        """
        temp = datetime.fromtimestamp(date)
        return str2uni(temp.strftime(u'%d-%m-%y %H:%M:%S'))

    def get_emperor_vassals(self, details=u'', system=None):
        """Get uwsgi emperor active vassals statistics
        
        :param server: host name
        """
        try:
            path_inventory = u'%s/inventories/%s' % (self.ansible_path, self.env)
            runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
            hosts = runner.get_inventory(group=system)
            self.json = []
            resp = []
            for host in hosts:
                res = self.__get_stats(host)
                vassals = res.pop(u'vassals')
                for vassal in vassals or []:
                    vassal[u'id'] = vassal[u'id']\
                                      .replace(u'/etc/uwsgi/vassals/', u'')\
                                      .replace(u'.ini', u'')
                    vassal.update({u'host':host})
                    for key in [u'first_run', u'last_run', u'last_ready', 
                                u'last_mod', u'last_accepting']:
                        vassal[key] = self.cdate(vassal[key])
                    resp.append(vassal)
    
            self.result(resp, headers=[u'host', u'pid', u'uid', u'gid', u'id', 
                                       u'first_run', u'last_run', u'last_ready', 
                                       u'last_mod', u'last_accepting'])
        except Exception as ex:
            self.error(ex)            
                            
    def get_emperor_blacklist(self, details=u'', system=None):
        """Get uwsgi emperor active vassals statistics
        
        :param server: host name
        """
        path_inventory = u'%s/inventories/%s' % (self.ansible_path, self.env)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
        hosts = runner.get_inventory(group=system)
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
    
    #
    # commands
    #
    @expose(help="Beehive management", hide=True)
    def default(self):
        self.app.args.print_help()

    @expose()
    def install(self):
        """Configure beehive nodes
        """
        run_data = {
            u'tags':[u'install']
        }        
        self.ansible_playbook(u'beehive', run_data, 
                              playbook=self.beehive_playbook)

    @expose()
    def hosts(self):
        """Configure beehive nodes hosts local resolution
        """
        run_data = {
            u'tags':[u'hosts']
        }        
        self.ansible_playbook(u'beehive', run_data, 
                              playbook=self.beehive_playbook)
    
    @expose()
    def configure(self):
        """Install beehive platform on beehive nodes
        """
        run_data = {
            u'tags':[u'configure']
        }        
        self.ansible_playbook(u'beehive', run_data, 
                              playbook=self.beehive_playbook)  
    
    @expose()
    def sync(self):
        """Sync beehive package an all nodes with remove git repository
        """
        run_data = {
            u'tags':[u'sync']
        }        
        self.ansible_playbook(u'beehive', run_data, 
                              playbook=self.beehive_playbook)
    
    @expose()
    def pip(self):
        """Sync beehive package an all nodes with remove git repository
        """
        run_data = {
            u'tags':[u'pip']
        }        
        self.ansible_playbook(u'beehive', run_data, 
                              playbook=self.beehive_playbook)   
    
    @expose()
    def subsystems(self):
        """List beehive subsystems
        """        
        self.get_emperor_nodes_stats(u'beehive')    
    
    @expose(aliases=[u'subsystem-create <subsystem>'], aliases_only=True)
    def subsystem_create(self):
        """Create beehive subsystem
    - subsystem: subsystem
        """
        subsystem = self.get_arg(name=u'subsystem')
        run_data = {
            u'subsystem':subsystem,
            u'tags':[u'subsystem']
        }        
        self.ansible_playbook(u'beehive-init', run_data, 
                              playbook=self.beehive_playbook)      
    
    @expose(aliases=[u'subsystem-update <subsystem>'], aliases_only=True)
    def subsystem_update(self):
        """Create beehive subsystem
    - subsystem: subsystem
        """
        subsystem = self.get_arg(name=u'subsystem')
        run_data = {
            u'subsystem':subsystem,
            u'tags':[u'subsystem'],
            u'create':False,
            u'update':True
        }
        self.ansible_playbook(u'beehive-init', run_data, 
                              playbook=self.beehive_playbook)        
    
    @expose(aliases=[u'instances [details=""]'], aliases_only=True)
    def instances(self):
        """List beehive subsystem instances
    - details: if True print details
        """
        details = self.get_arg(default=u'')  
        self.get_emperor_vassals(details, u'beehive')    
    
    @expose(aliases=[u'blacklist [details=""]'], aliases_only=True)
    def blacklist(self):
        """List beehive subsystem instances blacklist
    - details: if True print details
        """
        details = self.get_arg(default=u'')         
        self.get_emperor_blacklist(details, u'beehive')    
    
    @expose(aliases=[u'instance-sync <subsystem> <vassal>'], aliases_only=True)
    def instance_sync(self):
        """Sync beehive package an all nodes with local git repository and
        restart instances
    - subsystem: subsystem
    - vassal: vassal
        """
        subsystem = self.get_arg(name=u'subsystem')
        vassal  = self.get_arg(name=u'vassal')        
        run_data = {
            u'local_package_path':self.local_package_path,
            u'subsystem':subsystem,
            u'vassal':u'%s-%s' % (subsystem, vassal),
            u'tags':[u'sync-dev']
        }        
        self.ansible_playbook(u'beehive', run_data, 
                              playbook=self.beehive_playbook)
    
    @expose(aliases=[u'instance-deploy <subsystem> <vassal>'], aliases_only=True)
    def instance_deploy(self):
        """Deploy beehive instance for subsystem
    - subsystem: subsystem
    - vassal: vassal
        """
        subsystem = self.get_arg(name=u'subsystem')
        vassal  = self.get_arg(name=u'vassal')        
        run_data = {
            u'subsystem':subsystem,
            u'vassal':u'%s-%s' % (subsystem, vassal),
            u'tags':[u'deploy']
        }        
        self.ansible_playbook(u'beehive', run_data, 
                              playbook=self.beehive_playbook)
    
    @expose(aliases=[u'instance-undeploy <subsystem> <vassal>'], aliases_only=True)
    def instance_undeploy(self):
        """Undeploy beehive instance for subsystem
    - subsystem: subsystem
    - vassal: vassal
        """
        subsystem = self.get_arg(name=u'subsystem')
        vassal  = self.get_arg(name=u'vassal')        
        run_data = {
            u'subsystem':subsystem,
            u'vassal':u'%s-%s' % (subsystem, vassal),
            u'tags':[u'undeploy']
        }        
        self.ansible_playbook(u'beehive', run_data, 
                              playbook=self.beehive_playbook)
    
    @expose(aliases=[u'instance-ping [subsystem] [vassal]'], aliases_only=True)
    def instance_ping(self):
        """Ping beehive instance
    - subsystem: subsystem
    - vassal: vassal
        """
        subsystem = self.get_arg()
        vassal  = self.get_arg()        
        path_inventory = u'%s/inventories/%s' % (self.ansible_path, 
                                                 self.env)
        path_lib = u'%s/library/beehive/' % (self.ansible_path)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity, 
                        module=path_lib)
        hosts, vars = runner.get_inventory_with_vars(u'beehive')
        vars = runner.variable_manager.get_vars(runner.loader, host=hosts[0])
        instances = vars.get(u'instance')
        vassals = []
        if subsystem is not None and vassal is not None:
            vassals.append([subsystem, vassal])
        else:
            for instance in instances:
                vassals.append(instance.split(u'-'))
        
        resp = []
        for vassal in vassals:
            port = instances.get(u'%s-%s' % tuple(vassal)).get(u'port')
    
            for host in hosts:
                url = URL(u'http://%s:%s/v1.0/server/ping' % (host, port))
                logger.debug(url)
                http = HTTPClient(url.host, port=url.port, 
                                  headers={u'Content-Type':u'application/json'})
                try:
                    # issue a get request
                    response = http.get(url.request_uri)
                    # read status_code
                    response.status_code
                    # read response body
                    logger.debug(url.request_uri)
                    logger.debug(response.read())
                    res = json.loads(response.read())
                    # close connections
                    http.close()
                    if response.status_code == 200:
                        resp.append({u'subsystem':vassal[0], u'instance':vassal[1], 
                                     u'host':host, u'port':port, u'ping':True, 
                                     u'status':u'UP'})
                    else:
                        resp.append({u'subsystem':vassal[0], u'instance':vassal[1], 
                                     u'host':host, u'port':port, u'ping':False,
                                     u'status':u'UP'})
                except gevent.socket.error as ex:
                    logger.error(ex)
                    resp.append({u'subsystem':vassal[0], u'instance':vassal[1], 
                                 u'host':host, u'port':port, u'ping':False,
                                 u'status':u'DOWN'})
                except Exception as ex:
                    logger.error(ex)
                    resp.append({u'subsystem':vassal[0], u'instance':vassal[1], 
                                 u'host':host, u'port':port, u'ping':False,
                                 u'status':u'DOWN'})                    
                    
            
        self.result(resp, headers=[u'subsystem', u'instance', u'host', u'port', 
                                   u'ping', u'status'])
        
    @expose(aliases=[u'instance-log <subsystem> <vassal> [rows=100]'], aliases_only=True)
    def instance_log(self):
        """Execute command on managed platform nodes
    - group: ansible group
    - cmd: shell command   
        """
        group = self.get_arg(name=u'subsystem')
        vassal = self.get_arg(name=u'vassal')
        rows = self.get_arg(default=100)
        cmd  = u'tail -%s /var/log/beehive/beehive100/%s.log' % (rows, vassal)
        path_inventory = u'%s/inventories/%s' % (self.ansible_path, self.env)
        path_lib = u'%s/library/beehive/' % (self.ansible_path)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity, 
                        module=path_lib)
        tasks = [
            dict(action=dict(module=u'shell', args=cmd), register=u'shell_out'),
        ]
        runner.run_task(group, tasks=tasks, frmt=u'text')        
                
    '''def beehive_get_uwsgi_tree(self):
        """
        """
        self.__get_uwsgi_tree(self.env, u'beehive')'''
    
    @expose()
    def doc(self):
        """Make e deploy beehive documentation
        """
        run_data = {
            u'tags':[u'doc'],
            u'local_package_path':self.local_package_path
        }        
        self.ansible_playbook(u'docs', run_data, 
                              playbook=self.beehive_doc_playbook)          
        
platform_controller_handlers = [
    PlatformController,
    RedisController,
    MysqlController,
    NodeController,
    BeehiveController,
]
        
        