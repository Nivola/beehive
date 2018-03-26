"""
Created on Sep 22, 2017

@author: darkbk
"""
import os
import ujson as json
import urllib

import gevent
import sh
import copy
from time import time, sleep
from datetime import datetime
from httplib import HTTPConnection
import requests
from copy import deepcopy
from beecell.simple import str2uni
from beehive.manager.util.controller import BaseController, ApiController, check_error
from beecell.db.manager import RedisManager, MysqlManager
from cement.core.controller import expose
from geventhttpclient import HTTPClient
from geventhttpclient.url import URL
from logging import getLogger
import traceback
from beedrones.camunda.engine import WorkFlowEngine
from beedrones.openstack.client import OpenstackManager
from beedrones.vsphere.client import VsphereManager

from struct import pack, unpack
from datetime import datetime as dt
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto.rfc1902 import Integer, IpAddress, OctetString


logger = getLogger(__name__)

try:
    from beehive.manager.util.ansible2 import Runner
except Exception as ex:
    print(traceback.format_exc())
    print(u'ansible package not installed. %s' % ex)  


class PlatformController(BaseController):
    class Meta:
        label = 'platform'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Platform management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)

    @expose()
    @check_error
    def ping(self):
        """Ping
        """
        env = [u'-e', self.env]
        if self.envs is not None:
            env = [u'-E', u','.join(self.envs)]

        self.app.print_output(u'nginx:')
        res = sh.beehive(u'platform', u'nginx', u'ping', *env)
        print(res)
        self.app.print_output(u'mysql:')
        res = sh.beehive(u'platform', u'mysql', u'ping', *env)
        print(res)
        self.app.print_output(u'redis:')
        res = sh.beehive(u'platform', u'redis', u'ping', *env)
        print(res)
        self.app.print_output(u'redis-cluster:')
        res = sh.beehive(u'platform', u'redis-cluster', u'ping', *env)
        print(res)
        self.app.print_output(u'camunda:')
        res = sh.beehive(u'platform', u'camunda', u'ping', *env)
        print(res)
        self.app.print_output(u'openstack:')
        res = sh.beehive(u'platform', u'openstack', u'ping', *env)
        print(res)
        self.app.print_output(u'vsphere:')
        res = sh.beehive(u'platform', u'vsphere', u'ping', *env)
        print(res)
        self.app.print_output(u'cmp:')
        res = sh.beehive(u'platform', u'beehive', u'instance-ping', *env)
        print(res)


class AnsibleController(ApiController):
    class Meta:
        stacked_on = 'platform'
        stacked_type = 'nested'  

    def _setup(self, base_app):
        BaseController._setup(self, base_app)

        self.baseuri = u'/v1.0/resource'
        self.subsystem = u'resource'
        self.ansible_path = self.configs[u'ansible_path']
        # self.verbosity = self.app.pargs.verbosity
        self.main_playbook = u'%s/site.yml' % (self.ansible_path)
        self.create_playbook = u'%s/server.yml' % (self.ansible_path)
        self.site_playbook = u'%s/site.yml' % (self.ansible_path)
        self.beehive_playbook = u'%s/beehive.yml' % (self.ansible_path)
        self.beehive_doc_playbook = u'%s/beehive-doc.yml' % (self.ansible_path)
        self.local_package_path = self.configs[u'local_package_path']
    
    def _ext_parse_args(self):
        BaseController._ext_parse_args(self)
        self.verbosity = self.app.pargs.verbosity 
    
    #
    # ansible
    #
    def ansible_inventory(self, group=None):
        """list host by group
        
        **Parameters**:
        
            * **group**: ansible group
        """
        try:
            path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
            path_lib = u'%s/library/beehive/' % (self.ansible_path)
            runner = Runner(inventory=path_inventory, verbosity=self.verbosity, module=path_lib, vault_password=self.vault)
            res = runner.get_inventory(group)
            if isinstance(res, list):
                res = {group: res}
            logger.debug(u'Ansible inventory nodes: %s' % res)
            resp = []
            for k,v in res.items():
                resp.append({u'group':k, u'hosts':v})
            resp = sorted(resp, key=lambda x: x.get(u'group'))

            for i in resp:
                print(u'%30s : %s' % (i[u'group'], u', '.join(i[u'hosts'][:6])))
                for n in range(1, len(i[u'hosts'])/6):
                    print(u'%30s : %s' % (u'', u', '.join(i[u'hosts'][n*6:(n+1)*6])))
        except Exception as ex:
            self.error(ex)
    
    def ansible_playbook_run(self, group, run_data, playbook=None):
        """run playbook on group and host
        """
        try:
            path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
            path_lib = u'%s/library/beehive/' % self.ansible_path
            runner = Runner(inventory=path_inventory, verbosity=self.verbosity, module=path_lib, vault_password=self.vault)
            logger.debug(u'Create new ansible runner: %s' % runner)
            tags = run_data.pop(u'tags')
            if playbook is None:
                playbook = self.playbook
            runner.run_playbook(group, playbook, None, run_data, None, tags=tags, vault_password=self.vault)
            logger.debug(u'Run ansible playbook: %s' % playbook)
            runner = None
        except Exception as ex:
            self.error(ex)
    
    def ansible_playbook(self, group, run_data, playbook=None):
        from multiprocessing import Process
        p = Process(target=self.ansible_playbook_run, args=(group, run_data, playbook))
        p.start()
        logger.debug(u'Current process: %s' % os.getpid())
        logger.debug(u'Run ansible playbook as process: %s' % p.pid)
        p.join()
        logger.debug(u'Complete ansible playbook as process: %s' % p.pid)
    
    def ansible_task(self, group, cmd):
        """Run ansible tasks over a group of hosts
        
        :parma group: ansible host group
        :parma cmd: shell command
        """
        runners = self.get_runners()


        try:
            # path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
            # path_lib = u'%s/library/beehive/' % self.ansible_path
            # runner = Runner(inventory=path_inventory, verbosity=self.verbosity, module=path_lib, vault_password=self.vault)
            for runner in runners:
                tasks = [
                    dict(action=dict(module=u'shell', args=cmd), register=u'shell_out'),
                ]
                runner.run_task(group, tasks=tasks, frmt=u'text')
        except Exception as ex:
            self.error(ex)

    def get_runners(self):
        runners = []
        envs = [self.env]
        if self.envs is not None:
            envs = self.envs

        for env in envs:
            try:
                path_inventory = u'%s/inventory/%s' % (self.ansible_path, env)
                path_lib = u'%s/library/beehive/' % self.ansible_path
                runner = Runner(inventory=path_inventory, verbosity=self.verbosity, module=path_lib, vault_password=self.vault)
                runners.append(runner)
            except Exception as ex:
                self.error(ex, exc_info=1)
                raise
        logger.debug(u'Get runners for ansible envs: %s' % envs)
        return runners

    def get_hosts(self, runner, groups):
        all_hosts = []
        if not isinstance(groups, list):
            groups = [groups]
        for group in groups:
            hosts, vars = runner.get_inventory_with_vars(group)
            all_hosts.extend(hosts)

        logger.debug(u'Get hosts from ansible groups %s: %s' % (groups, all_hosts))
        return all_hosts

    def get_hosts_vars(self, runner, groups):
        all_vars = {}
        if not isinstance(groups, list):
            groups = [groups]
        for group in groups:
            hosts_vars = runner.variable_manager.get_vars(runner.loader)
            all_vars.update(hosts_vars)
        logger.debug(u'Get hosts vars from ansible inventory: %s' % all_vars)
        return hosts_vars

    def get_multi_hosts(self, groups):
        runners = self.get_runners()
        all_hosts = []
        for runner in runners:
            hosts = self.get_hosts(runner, groups)
            all_hosts.extend(hosts)
        logger.debug(u'Get hosts from ansible groups %s: %s' % (groups, all_hosts))
        return all_hosts


class NginxController(AnsibleController):
    class Meta:
        label = 'nginx'
        description = "Nginx management"

    def run_cmd(self, func):
        """Run command on redis instances
        """
        hosts = self.get_multi_hosts(u'nginx')

        try:
            resp = []
            for host in hosts:
                res = func(str(host))
                resp.append({u'host': str(host), u'response': res})
                logger.info(u'Exec %s on ngninx server %s : %s' % (func.__name__, str(host), resp))
            self.result(resp, headers=[u'host', u'response'], maxsize=200)
        except Exception as ex:
            self.error(ex)

    @expose(aliases=[u'ping [port=]'], aliases_only=True)
    @check_error
    def ping(self):
        """Ping nginx instances
        """
        port = self.get_arg(name=u'port', default=443, keyvalue=True)

        def func(server):
            try:
                proxies = {
                    u'http': None,
                    u'https': None,
                }
                res = requests.get(u'https://%s:%s' % (server, port), proxies=proxies, verify=False)
                logger.debug(u'uri: https://%s:%s' % (server, port))
                if res.status_code == 200:
                    res = True
                else:
                    res = False
            except:
                logger.warn(u'', exc_info=1)
                res = False

            return res

        self.run_cmd(func)

    @expose(aliases=[u'status [port=]'], aliases_only=True)
    @check_error
    def status(self):
        """nginx instances status
        """
        port = self.get_arg(name=u'port', default=443, keyvalue=True)

        def func(server):
            try:
                proxies = {
                    u'http': None,
                    u'https': None,
                }
                res = requests.get(u'https://%s:%s/nginx_status' % (server, port), proxies=proxies, verify=False)
                logger.debug(u'uri: https://%s:%s' % (server, port))
                if res.status_code == 200:
                    data = res.content.split(u'\n')
                    for item in range(0,len(data)):
                        data[item] = data[item].split(u' ')
                    res = {
                        u'conns': {
                            u'active': int(data[0][2]),
                            u'accepts': int(data[2][1]),
                            u'handled': int(data[2][2]),
                            u'requests': int(data[2][3]),
                            u'reading': int(data[3][1]),
                            u'writing': int(data[3][3]),
                            u'waiting': int(data[3][5]),
                        }
                    }
                else:
                    print res
            except:
                logger.warn(u'', exc_info=1)
                res = False

            return res

        self.run_cmd(func)

    @expose()
    @check_error
    def engine_status(self):
        """Status of nginx instances
        """
        self.ansible_task(u'nginx', u'systemctl status nginx')

    @expose()
    @check_error
    def engine_start(self):
        """Start nginx instances
        """
        self.ansible_task(u'nginx', u'systemctl start nginx')

    @expose()
    @check_error
    def engine_stop(self):
        """Start nginx instances
        """
        self.ansible_task(u'nginx', u'systemctl stop nginx')


class RedisController(AnsibleController):
    class Meta:
        label = 'redis'
        description = "Redis management"
        
    def run_cmd(self, func, dbs=[0]):
        """Run command on redis instances
        """
        '''try:
            path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
            path_lib = u'%s/library/beehive/' % (self.ansible_path)
            runner = Runner(inventory=path_inventory, verbosity=self.verbosity, module=path_lib, vault_password=self.vault)
            hosts, vars = runner.get_inventory_with_vars(u'redis')        

        except Exception as ex:
            self.error(ex)
            return'''

        hosts = self.get_multi_hosts(u'redis')
            
        try:
            resp = []
            for host in hosts:
                for db in dbs:
                    uri = u'redis://%s:%s/%s' % (host, 6379, db)
                    logger.warn(uri)
                    server = RedisManager(uri)
                    res = func(server)
                    
                    if isinstance(res, dict):
                        for k, v in res.items():
                            resp.append({u'host': str(host), u'db': db, u'response': u'%s = %s' % (k, v)})
                    elif isinstance(res, list):
                        for v in res:
                            resp.append({u'host': str(host), u'db': db, u'response': v})
                    else:
                        resp.append({u'host': str(host), u'db': db, u'response': res})
            self.result(resp, headers=[u'host', u'db', u'response'])
        except Exception as ex:
            self.error(ex)         
        
    @expose()
    @check_error
    def ping(self):
        """Ping redis instances
        """        
        def func(server):
            return server.ping()
        self.run_cmd(func)
    
    @expose()
    @check_error
    def info(self):
        """Info from redis instances
        """        
        def func(server):
            return server.info()
        self.run_cmd(func)
    
    @expose()
    @check_error
    def config(self):
        """Config of redis instances
        """        
        def func(server):
            return server.config()
        self.run_cmd(func) 
    
    @expose()
    @check_error
    def summary(self):
        """Info from redis instances
        """        
        def func(server):
            res = server.info()
            resp = {}
            for k,v in res.items():
                raw = {}
                for k1 in [u'role', u'redis_version', u'process_id', u'uptime_in_seconds', u'os', u'connected_clients',
                           u'total_commands_processed', u'pubsub_channels', u'total_system_memory_human',
                           u'used_memory_rss_human', u'used_memory_human', u'used_cpu_sys', u'used_cpu_user',
                           u'instantaneous_output_kbps']:
                    raw[k1] = v[k1]
                resp[k] = raw
            return resp
        self.run_cmd(func)    
    
    @expose()
    @check_error
    def size(self):
        """Size of redis instances
        """
        def func(server):
            return server.size()
        self.run_cmd(func, dbs=range(0,8))
    
    @expose()
    @check_error
    def client_list(self):
        """Client list of redis instances
        """        
        def func(server):
            return server.server.client_list()
        self.run_cmd(func)         
    
    @expose()
    @check_error
    def flush(self):
        """Flush redis instances
        """        
        def func(server):
            return server.server.flushall()
        self.run_cmd(func)  
    
    @expose(aliases=[u'inspect [pattern]'], aliases_only=True)
    @check_error
    def inspect(self):
        """Inspect redis instances
    - pattern: keys search pattern [default=*]
        """        
        pattern = self.get_arg(default=u'*')
        
        def func(server): 
            return server.inspect(pattern=pattern, debug=False)
        self.run_cmd(func, dbs=range(0, 8))
    
    @expose(aliases=[u'query [pattern]'], aliases_only=True)
    @check_error
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
                for k, v in res.items():
                    resp.append({k: len(v)})
                return resp
            return res
        self.run_cmd(func, dbs=range(0, 8))
    
    @expose(aliases=[u'delete [pattern]'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete redis instances keys.
    - pattern: keys search pattern [default=*]
        """        
        pattern = self.get_arg(default=u'*')
        
        def func(server):
            return server.delete(pattern=pattern)
        self.run_cmd(func, dbs=range(0, 8))


class RedisClutserController(RedisController):
    class Meta:
        label = 'redis-cluster'
        description = "Redis Cluster management"
        
    def run_cmd(self, func, dbs=[0]):
        """Run command on redis instances
        """
        '''try:
            path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
            path_lib = u'%s/library/beehive/' % (self.ansible_path)
            runner = Runner(inventory=path_inventory, verbosity=self.verbosity, module=path_lib, vault_password=self.vault)
            cluster_hosts, vars = runner.get_inventory_with_vars(u'redis-master')
        except Exception as ex:
            self.error(ex)
            return'''

        hosts = self.get_multi_hosts(u'redis-master')

        try:
            # redis cluster
            resp = []
            headers = []
            cluster_nodes = []
            redis_uri = u'redis-cluster://'
            for host in hosts:
                cluster_nodes.append(u'%s:%s' % (str(host), u'6379'))
            redis_uri += u','.join(cluster_nodes)
            server = RedisManager(redis_uri)
            res = func(server)
            try:
                values = res.values()
            except:
                values = [None]

            if isinstance(values[0], dict):
                headers = res.keys()
                raws = {}
                # loop over hosts
                for key, values in res.items():
                    # loop over hosts fields
                    for k1,v1 in values.items():
                        try:
                            # assign new host
                            raws[k1][key] = v1
                        except:
                            # create new raw
                            raws[k1] = {u'fields': k1, key: v1}
                headers.insert(0, u'fields')
                resp = raws.values()
            elif isinstance(res, dict):
                resp = res
                headers = resp.keys()                
            elif isinstance(res, list):
                resp = res
                headers = [u'keys']                

            logger.info(u'Cmd redis : %s' % (resp))
            self.result(resp, headers=headers, key_separator=u',', maxsize=25)            
        except Exception as ex:
            self.error(ex)            
        
    @expose()
    @check_error
    def super_ping(self):
        """Ping single redis instances in a cluster
        """
        '''try:
            path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
            path_lib = u'%s/library/beehive/' % (self.ansible_path)
            runner = Runner(inventory=path_inventory, verbosity=self.verbosity, 
                            module=path_lib, vault_password=self.vault)
            cluster_hosts, vars = runner.get_inventory_with_vars(u'redis-cluster')
        except Exception as ex:
            self.error(ex)
            return'''

        hosts = self.get_multi_hosts(u'redis-cluster')

        # redis cluster
        resp = []
        headers = []
        cluster_nodes = []
        db = 0
        for host in hosts:
            redis_uri = u'redis://%s:%s/%s' % (str(host), u'6379', db)
            server = RedisManager(redis_uri, timeout=2)
            res = server.ping()
            resp.append({u'host': str(host), u'db': db, u'response': res})
        
        logger.info(u'Ping redis : %s' % resp)
        self.result(resp, headers=[u'host', u'db', u'response'])
        
    @expose()
    @check_error
    def cluster_nodes(self):
        """
        """
        '''try:
            path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
            path_lib = u'%s/library/beehive/' % (self.ansible_path)
            runner = Runner(inventory=path_inventory, verbosity=self.verbosity, 
                            module=path_lib, vault_password=self.vault)
            cluster_hosts, vars = runner.get_inventory_with_vars(u'redis-master')
        except Exception as ex:
            self.error(ex)
            return'''

        hosts = self.get_multi_hosts(u'redis-master')

        # redis cluster
        cluster_nodes = []
        redis_uri = u'redis-cluster://'
        for host in hosts:
            cluster_nodes.append(u'%s:%s' % (str(host), u'6379'))
        redis_uri += u','.join(cluster_nodes)
        server = RedisManager(redis_uri)
        resp = server.server.cluster_nodes()
        logger.info(u'Cmd redis : %s' % (resp))
        self.result(resp, headers=[u'host', u'id', u'port', u'link-state', u'flags', u'master', u'ping-sent',
                    u'pong-recv'], key_separator=u',', maxsize=25)


class MysqlController(AnsibleController):
    class Meta:
        label = 'mysql'
        description = "Mysql management"

    def __get_engine(self, host, port, user, db):
        db_uri = u'mysql+pymysql://%s:%s@%s:%s/%s' % (user[u'name'], user[u'password'], host, port, db)
        server = MysqlManager(1, db_uri)
        server.create_simple_engine()
        logger.info(u'Get mysql engine for %s' % (db_uri))
        return server
    
    def __get_hosts(self):
        runners = self.get_runners()
        hosts = []
        for runner in runners:
            hosts = self.get_hosts(runner, [u'mysql-cluster'])
            if len(hosts) == 0:
                hosts.extend(self.get_hosts(runner, [u'mysql']))
        vars = runner.variable_manager.get_vars(runner.loader, host=hosts[0])
        root = {u'name': u'root', u'password': vars[u'mysql'][u'root_remote_pwd']}
        return [str(h) for h in hosts], root
    
    @expose(aliases=[u'ping [port]'], aliases_only=True)
    @check_error
    def ping(self):
        """Test mysql instance
    - port: instance port [default=3306]
        """
        port = self.get_arg(default=3306)
        hosts, root = self.__get_hosts()

        resp = []
        db = u'sys'
        for host in hosts:
            server = self.__get_engine(host, port, root, db)
            res = server.ping()
            resp.append({u'host': host, u'response': res})
            logger.info(u'Ping mysql : %s' % (res))
        
        self.result(resp, headers=[u'host', u'response'])

    @expose(aliases=[u'cluster-status [port=] [check_host=]'], aliases_only=True)
    @check_error
    def cluster_status(self):
        """Get mysql cluster status
    - port: instance port [default=3306]
        """
        port = self.get_arg(name=u'port', default=3306, keyvalue=True)
        check_host = self.get_arg(name=u'check_host', default=None, keyvalue=True)
        hosts, root = self.__get_hosts()
        if check_host is not None:
            hosts = [check_host]

        resp = []
        db = u'sys'
        for host in hosts:
            try:
                server = self.__get_engine(host, port, root, db)
                status = server.get_cluster_status().values()
                logger.info(u'Get mysql cluster status : %s' % status)
                for item in status:
                    item.update({u'check_host': host})
                    resp.append(item)
            except Exception as ex:
                self.error(ex)

        self.result(resp, headers=[u'check_host', u'MEMBER_HOST', u'MEMBER_PORT', u'MEMBER_STATE'])

    @expose(aliases=[u'schemas [port]'], aliases_only=True)
    @check_error
    def schemas(self):
        """Get mysql schemas list
    - port: instance port [default=3306]
        """
        port = self.get_arg(default=3306)
        hosts, root = self.__get_hosts()

        resp = {}
        db = u'sys'
        headers = [u'schema']
        for host in hosts:
            headers.append(u'%s.tables' % host)
        for host in hosts:
            self.app.print_output(u'Host: %s' % host)
            server = self.__get_engine(host, port, root, db)
            schemas = server.get_schemas()
            for schema_table in schemas:
                schema = schema_table[u'schema']
                tables = schema_table[u'tables']
                if schema not in resp:
                    resp[schema] = {u'schema': schema}
                    for h in hosts:
                        resp[schema][u'%s.tables' % h] = None
                resp[schema][u'%s.tables' % host] = tables
            logger.info(u'Get mysql schemas : %s' % (resp))
        
        self.result(resp.values(), headers=headers, key_separator=u',')
        
    @expose()
    @check_error
    def schemas_update(self):
        """Update mysql users and schemas
        """
        run_data = {
            u'tags': [u'schema']
        }        
        self.ansible_playbook(u'mysql', run_data, playbook=u'%s/mysql.yml' % self.ansible_path)
        self.ansible_playbook(u'mysql-cluster-master', run_data, playbook=u'%s/mysql-cluster.yml' % self.ansible_path)
        
    @expose(aliases=[u'users [port]'], aliases_only=True)
    @check_error
    def users(self):
        """Get mysql users list
    - port: instance port [default=3306]
        """
        port = self.get_arg(default=3306)
        hosts, root = self.__get_hosts()

        resp = {}
        db = u'sys'
        headers = [u'user']
        for host in hosts:
            headers.append(u'%s.hosts' % host)
        for host in hosts:
            self.app.print_output(u'Host: %s' % host)
            server = self.__get_engine(host, port, root, db)
            users = server.get_users()
            for user_host in users:
                uhost = user_host[u'host']
                user = user_host[u'user']
                if user not in resp:
                    resp[user] = {u'user': user}
                    for h in hosts:
                        resp[user][u'%s.hosts' % h] = None
                resp[user][u'%s.hosts' % host] = uhost
            logger.info(u'Get mysql users : %s' % resp)
        self.result(resp.values(), headers=headers, key_separator=u',')


        '''for host in hosts:
            self.app.print_output(u'Host: %s' % host)
            server = self.__get_engine(host, port, root, db)
            resp = server.get_users()
            logger.info(u'Get mysql users : %s' % (resp))
        
            self.result(resp, headers=[u'host', u'user'])'''

    @expose(aliases=[u'tables-check <schema> [port]'], aliases_only=True)
    @check_error
    def tables_check(self):
        """Get mysql users list
    - schema: schema name
    - port: instance port [default=3306]
        """
        schema = self.get_arg(name=u'schema')
        port = self.get_arg(default=3306)
        hosts, root = self.__get_hosts()

        resp = {}
        db = u'sys'
        headers = [u'table']
        for host in hosts:
            headers.append(u'%s.rows-inc' % host)
        for host in hosts:
            self.app.print_output(u'Host: %s' % host)
            server = self.__get_engine(host, port, root, db)
            tables = server.get_schema_tables(schema)
            for table_row in tables:
                table = table_row[u'table_name']
                rows = table_row[u'table_rows']
                inc = table_row[u'auto_increment']
                if table not in resp:
                    resp[table] = {u'table': table}
                    for h in hosts:
                        resp[table][u'%s.rows-inc' % h] = None
                resp[table][u'%s.rows-inc' % host] = u'%-8s %-8s' % (rows, inc)
            logger.info(u'Get mysql tables : %s' % resp)
        self.result(resp.values(), headers=headers, key_separator=u',')

    @expose(aliases=[u'tables <schema> [port]'], aliases_only=True)
    @check_error
    def tables(self):
        """Get mysql schema table list
    - port: instance port [default=3306]
        """
        schema = self.get_arg(name=u'schema')
        port = self.get_arg(default=3306)
        hosts, root = self.__get_hosts()

        resp = []
        db = u'sys'
        for host in hosts:
            self.app.print_output(u'Host: %s' % host)
            server = self.__get_engine(host, port, root, db)
            resp = server.get_schema_tables(schema)
            logger.info(u'Get mysql schema %s tables : %s' % (schema, resp))
        
            self.result(resp, headers=[u'table_name', u'table_rows', u'auto_increment', u'data_length',
                                       u'index_length'])
        
    @expose(aliases=[u'table-description <schema> <table> [port]'], aliases_only=True)
    @check_error
    def table_description(self):
        """Get mysql schema table description
    - port: instance port [default=3306]
        """
        schema = self.get_arg(name=u'schema')
        table = self.get_arg(name=u'table')
        port = self.get_arg(default=3306)
        hosts, root = self.__get_hosts()

        resp = []
        for host in hosts:
            self.app.print_output(u'Host: %s' % host)
            server = self.__get_engine(host, port, root, schema)
            resp = server.get_table_description(table)
            logger.info(u'Get mysql schema %s table %s descs : %s' % (schema, table, resp))
        
            self.result(resp, headers=[u'name', u'type', u'default', u'index', u'is_primary_key', u'is_nullable',
                                       u'is_unique'])

    @expose(aliases=[u'table-query <schema> <table> [rows] [offset] [port]'], aliases_only=True)
    @check_error
    def table_query(self):
        """Get mysql schema table query
    - port: instance port [default=3306]
        """
        schema = self.get_arg(name=u'schema')
        table = self.get_arg(name=u'table')
        rows = self.get_arg(default=20)
        offset = self.get_arg(default=0)
        port = self.get_arg(default=3306)
        hosts, root = self.__get_hosts()

        for host in hosts:
            self.app.print_output(u'Host: %s' % host)
            server = self.__get_engine(host, port, root, schema)
            resp = server.query_table(table, where=None, fields="*", rows=rows, offset=offset)
            logger.info(u'Get mysql schema %s table %s query : %s' % (schema, table, resp))
        
            self.result(resp, headers=resp[0].keys(), maxsize=20) 

    @expose(aliases=[u'drop-all-tables <schema>'], aliases_only=True)
    @check_error
    def drop_all_tables(self):
        """Get mysql schema table query
        """
        schema = self.get_arg(name=u'schema')
        port = self.get_arg(default=3306)
        hosts, root = self.__get_hosts()

        for host in hosts:
            self.app.print_output(u'Host: %s' % host)
            server = self.__get_engine(host, port, root, schema)
            resp = server.drop_all_tables(schema)
            msg = {u'msg': u'drop all tables in schema %s' % schema}
            logger.info(msg)
            self.result(msg, headers=[u'msg'])


class CamundaController(AnsibleController):
    class Meta:
        label = 'camunda'
        description = "Camunda management"
    
    def __get_engine(self, port=8080):
        path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
        path_lib = u'%s/library/beehive/' % (self.ansible_path)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity, module=path_lib, vault_password=self.vault)
        hosts, vars = runner.get_inventory_with_vars(u'camunda')
        
        clients = []
        for host in hosts:
            conn = {
                u'host': str(host),
                u'port': port,
                u'path': u'/engine-rest',
                u'proto': u'http'
            }
            user = u'admin'
            passwd = u'camunda'
            proxy = None
            keyfile=None
            certfile=None
            client = WorkFlowEngine(conn, user=user, passwd=passwd,
                proxy=proxy, keyfile=keyfile, certfile=certfile)
            clients.append(client)
        return clients

    def camunda_engine(self, port=8080):
        return self.__get_engine( port)

    @expose(help="Camunda management", hide=True)
    @check_error
    def default(self):
        self.app.args.print_help()
    
    @expose(aliases=[u'ping [port]'], aliases_only=True)
    @check_error
    def ping(self):
        """Test camunda instance
        - user: user
        - pwd: user password
        - db: db schema
        - port: instance port [default=3306]
        """
        port = self.get_arg(default=8080)
        clients = self.__get_engine(port=port)
        resp = []
        for client in clients:
            res = client.ping()
            resp.append({u'host':client.connection.get(u'host'), u'response':res})
        logger.debug(u'Ping camunda: %s' % resp)
        self.result(resp, headers=[u'host', u'response'])           


class CamundaDeployController(CamundaController):
    class Meta:
        stacked_on = 'camunda'
        label = 'deploy'
        description = "Camunda deploy  management"

    @expose(aliases=[ u'file' , u'file <bpmn> [port]'], aliases_only=True)
    @check_error
    def deploy(self):
        """Deploy a proces defintion to engine
        - <bpmn> a file containtg porces bpm definition
        - [port] optionaleport
        """
        filename = self.get_arg(name=u'bpmn')
        port = self.get_arg(name=u'port',default=8080)
        clients = self.camunda_engine(port=port) #__get_engine(port=port)
        resp = []
        if os.path.isfile(filename):
            f = open(filename, 'r')
            content = f.read()
            f.close()
            name,dtype = os.path.splitext(os.path.split(filename)[1])
            dtype = dtype[1:]
        else:
            raise Exception(u'bpmn %s is not a file' % filename)
            
        for client in clients:
            res = client.process_deployment_create( content.rstrip(), name, type=dtype, checkduplicate=True, changeonly=True, tenantid=None)
            resp.append({u'host':client.connection.get(u'host'), u'response':res})
        logger.debug(u'camunda deploy: %s' % resp)
        self.result(resp, headers=[u'host', u'response'])           

    @expose(aliases=[u'list'], aliases_only=True)
    @check_error
    def deploylist(self):
        """ 
            get a list of proceses defined  
            [port] optional port
        """
        port = self.get_arg(name=u'port',default=8080)
        clients = self.camunda_engine(port=port) #__get_engine(port=port)
        resp = []
        for client in clients:
            # plist =  json.decode(client.process_definition_list() )
            plist =  client.process_deployment_list() 
            # print plist
            for deploy in plist:
                resp.append({
                    u'host': client.connection.get(u'host'), 
                    u"id": deploy[u"id"],
                    u"name": deploy[u"name"],
                    u"source": deploy[u"source"],
                    u"deploymentTime": deploy[u"deploymentTime"],
                    })
        self.result(resp, headers=[ 
            u'host', 
            u"id",
            u"name",
            u"source",
            u"deploymentTime",
            ])
    
    # TODO  delete deploy
    @expose(aliases=[u'delete', u'delete <id>'], aliases_only=True)
    @check_error
    def deldeploy(self):
        """ 
            <id> [port]
            Delete a deploy and all process definition and running instances 
            <id>  the definitin id from deploy list    
            [port] optional port
        """
        deployid = self.get_arg(name=u'id')
        
        port = self.get_arg(name=u'port',default=8080)
        clients = self.camunda_engine(port=port) #__get_engine(port=port)
        resp = []
        
        for client in clients:
            try:
                result =  client.process_deployment_delete ( deployid) 
                resp.append({ u'host': client.connection.get(u'host'), u'status': u'OK', })
            except  :
                resp.append({ u'host': client.connection.get(u'host'), u'status': u'KO', })

        self.result(resp, headers=[ 
            u'host', 
            u'status' , 
            ])


class CamundaProcessController(CamundaController):
    class Meta:
        stacked_on = 'camunda'
        label = 'process'
        description = "Camunda process  management"

    @expose(aliases=[u'start <key>  <jsonparams> [port]'], aliases_only=True)
    @check_error
    def start(self):
        """ 
            start a process instance 
            <key>  the proces key to be started
            <jsonparams>  the json definition of proces variables, support '@' operator json file
            [port] optional port
        """
        key = self.get_arg(name=u'key')
        jsonparams = self.get_arg(name=u'jsonparams',default=u'{}' )
        if jsonparams[0] == '@':
            filename=jsonparams[1:]
            if os.path.isfile(filename):
                f = open(filename, 'r')
                jsonparams = f.read()
                f.close()
            else:
               raise Exception(u'json specification %s is not a file' % filename)
        port = self.get_arg(name=u'port',default=8080)
        clients = self.camunda_engine(port=port) # __get_engine(port=port)
        resp = []
        paramdict = json.decode(jsonparams)
        for client in clients:
            # client.process_instance_start_processkey ( key, businessKey=None, variables=paramdict)
            res = client.process_instance_start_processkey ( key,  variables=paramdict)
            resp.append({u'host':client.connection.get(u'host'), u'response':res})
        logger.debug(u'camunda start: %s' % resp)
        self.result(resp, headers=[u'host', u'response'])
    
    @expose(aliases=[u'list'], aliases_only=True)
    @check_error
    def processlist(self):
        """ 
            get a list of proceses defined  
            [port] optional port
        """
        port = self.get_arg(name=u'port',default=8080)
        clients = self.camunda_engine(port=port) # __get_engine(port=port)
        resp = []
        for client in clients:
            # plist =  json.decode(client.process_definition_list() )
            plist =  client.process_definition_list() 
            # print plist
            for definition in plist:
                resp.append({
                    u'host': client.connection.get(u'host'), 
                    u'id': definition[u'id'], 
                    u'key': definition[u'key'],
                    # u'category': definition[u'category'],
                    u'description': definition[u'description'] ,
                    u'name': definition[u'name'],
                    u'version': definition[u'version'],
                    u'resource': definition[u'resource'] ,
                    # u'deploymentId': definition[u'deploymentId'],
                    # u'diagram': definition[u'diagram'] ,
                    u'suspended': definition[u'suspended'],
                    # u'tenantId': definition[u'tenantId'],
                    u'versionTag': definition[u'versionTag'],
                    # u'historyTimeToLive': definition[u'historyTimeToLive'],
                    })
        logger.debug(u'camunda proceslist: %s' % resp)
        self.result(resp, headers=[ 
            u'host', 
            u'id' , 
            u'key', 
            # u'category', 
            u'description',
            u'name',
            u'version', 
            u'resource', 
            # u'deploymentId',  
            #u'diagram',
            u'suspended', 
            # u'tenantId', 
            u'versionTag', 
            # u'historyTimeToLive', 
            ])

    @expose(aliases=[u'delete',u'delete  [id=]  [key=] [version=] [port]'], aliases_only=True)
    @check_error
    def deldefinition(self):
        """ 
            Delete a process definition and al runing unsace
            in order to identify the process definition to be deleted use his id or the key and version 
            id the definitin id (from list)    

            key the process key (fromn list)
            version the porcess version (from list)
            [port] optional port
        """
        params = self.get_query_params(*self.app.pargs.extra_arguments)
        # logger.debug (params)
        port = self.get_arg(name=u'port',default=8080)
        clients = self.camunda_engine(port=port) #__get_engine(port=port)
        resp = []
        
        for client in clients:
            if params.has_key("id"):
                did = params["id"]
            elif params.has_key ("key") and params.has_key("version") :
                key = params["key"]
                version = params["version"]
                plist =  client.process_definition_list()
                for definition in plist:
                    if definition[u'key'] == key and definition[u'version']:
                        did = definition[u'id']
                        break
            else:
                did = None
            logger.debug ("definitionid : " + str(did)  )
            try:
                result =  client.process_definition_delete( did) 
                resp.append({ u'host': client.connection.get(u'host'), u'status': u'OK', })
            except  :
                resp.append({ u'host': client.connection.get(u'host'), u'status': u'KO', })

        self.result(resp, headers=[ 
            u'host', 
            u'status',
            ])


class VsphereController(AnsibleController):
    class Meta:
        label = 'platform.vsphere'
        aliases = ['vsphere']
        aliases_only = True
        description = "Vsphere management"

    def __get_orchestartors(self, instances, vip=True):
        """
        """
        envs = [self.env]
        if self.envs is not None:
            envs = self.envs

        orchestrators = {}
        for env in envs:
            os = self.configs[u'environments'][env][u'orchestrators'].get(u'vsphere')
            orchestrators.update(os)

        orchestrators_available = orchestrators.keys()

        confs = []
        if instances is None:
            instances = orchestrators_available
        else:
            instances = instances.split(u',')
        for instance in instances:
            if instance not in orchestrators_available:
                logger.error(u'Select orchestrators among: %s' % orchestrators_available)
                raise Exception(u'Select orchestrators among: %s' % orchestrators_available)

            conf = orchestrators.get(instance)
            new_conf = deepcopy(conf)
            new_conf[u'instance'] = instance
            new_conf[u'host'] = new_conf[u'vcenter'][u'host']
            confs.append(new_conf)
        logger.warn(u'Get vsphere configs: %s' % confs)
        return confs

    def __get_client(self, conf):
        """
        """
        client = VsphereManager(conf.get(u'vcenter'), conf.get(u'nsx'), key=self.key)
        # client.authorize(conf.get(u'user'), conf.get(u'pwd'), project=conf.get(u'project'), domain=conf.get(u'domain'))
        return client

    def run_cmd(self, func, configs):
        """Run command on vsphere instances

        **Parameters:**

            * **configs**: list of dictionary with openstack connection config
        """
        try:
            resp = []
            for config in configs:
                start = time()
                res = func(config)
                elapsed = time() - start
                resp.append({u'instance': config[u'instance'],
                             u'host': config[u'host'],
                             u'elapsed': elapsed, u'response': res})
                logger.info(u'Query vsphere %s : %s' % (config[u'host'], elapsed))
            self.result(resp, headers=[u'instance', u'host', u'elapsed', u'response'], maxsize=300)
        except Exception as ex:
            self.error(ex)

    @expose(aliases=[u'ping [instances] [vip=true/false]'], aliases_only=True)
    @check_error
    def ping(self):
        """Ping vsphere instances
    - instances: comma separated vsphere instances
    - vip: if true query only the vip [default=True]
        """
        instances = self.get_arg(default=None)
        vip = self.get_arg(default=True, name=u'vip', keyvalue=True)

        def func(conf):
            res = {u'vpshere': False, u'nsx': False}
            try:
                client = self.__get_client(conf)
                res[u'vpshere'] = client.system.ping_vsphere()
                res[u'nsx'] = client.system.ping_nsx()
            except Exception as ex:
                logger.error(ex, exc_info=1)

            return res

        configs = self.__get_orchestartors(instances, vip=vip)
        self.run_cmd(func, configs)


class OpenstackController(AnsibleController):
    class Meta:
        label = 'platform.openstack'
        aliases = ['openstack']
        aliases_only = True
        description = "Openstack management"

    def __get_orchestartors(self, instances, vip=True):
        """
        """
        envs = [self.env]
        if self.envs is not None:
            envs = self.envs

        orchestrators = {}
        for env in envs:
            os = self.configs[u'environments'][env][u'orchestrators'].get(u'openstack')
            orchestrators.update(os)

        orchestrators_available = orchestrators.keys()

        confs = []
        if instances is None:
            instances = orchestrators_available
        else:
            instances = instances.split(u',')
        for instance in instances:
            if instance not in orchestrators_available:
                logger.error(u'Select orchestrators among: %s' % orchestrators_available)
                raise Exception(u'Select orchestrators among: %s' % orchestrators_available)

            conf = orchestrators.get(instance)
            uris = conf.pop(u'uris')
            if vip is True:
                uris = [conf.get(u'uri')]
            for uri in uris:
                new_conf = deepcopy(conf)
                new_conf[u'instance'] = instance
                new_conf[u'uri'] = uri
                new_conf[u'host'] = uri.split(u'//')[1].split(u':')[0]
                confs.append(new_conf)
        logger.warn(u'Get openstack configs: %s' % confs)
        return confs

    def __get_client(self, conf):
        """
        """
        client = OpenstackManager(conf.get(u'uri'), default_region=conf.get(u'region'))
        client.authorize(conf.get(u'user'), conf.get(u'pwd'), project=conf.get(u'project'), domain=conf.get(u'domain'),
                         key=self.key)
        return client
    
    def run_cmd(self, func, configs):
        """Run command on openstack instances
        
        **Parameters:**

            * **configs**: list of dictionary with openstack connection config

            * **instance** (:py:class:`str`): openstack label reference used in 
                ansible to list the nodes
            * **subset** (:py:class:`str`): node subset. Use "controller", 
                "compute" or "" for all nodes
            * **authorize** (:py:class:`str`): if True check permissions for authorization
        """
        try:
            '''inventory = u'openstack-%s' % instance
            if subset != u'':
                inventory = u'%s-%s' % (inventory, subset)
            path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
            path_lib = u'%s/library/beehive/' % self.ansible_path
            runner = Runner(inventory=path_inventory, verbosity=self.verbosity, module=path_lib, vault_password=self.vault)
            hosts, vars = runner.get_inventory_with_vars(inventory)'''

            resp = []
            for config in configs:
                start = time()
                res = func(config)
                elapsed = time() - start
                resp.append({u'instance': config[u'instance'],
                             u'host': config[u'host'],
                             u'elapsed': elapsed, u'response': res})
                logger.info(u'Query openstack %s : %s' % (config[u'host'], elapsed))
            self.result(resp, headers=[u'instance', u'host', u'elapsed', u'response'], maxsize=300)
        except Exception as ex:
            self.error(ex)            

    @expose(aliases=[u'ping [instances] [vip=true/false]'], aliases_only=True)
    @check_error
    def ping(self):
        """Ping openstack instances
    - instances: comma separated openstack instances
    - vip: if true query only the vip [default=True]
        """
        instances = self.get_arg(default=None)
        vip = self.get_arg(default=True, name=u'vip', keyvalue=True)

        def func(conf):
            try:
                client = self.__get_client(conf)
                # client.server.list()
                client.ping()
            except Exception as ex:
                logger.error(ex, exc_info=1)
                return False
            return True

        configs = self.__get_orchestartors(instances, vip=vip)
        self.run_cmd(func, configs)

    @expose(aliases=[u'ping2 [instances] [vip=true/false]'], aliases_only=True)
    @check_error
    def ping2(self):
        """Ping openstack instances using an heavy query
    - instances: comma separated openstack instances
    - vip: if true query only the vip [default=True]
        """
        instances = self.get_arg(default=None)
        vip = self.get_arg(default=True, name=u'vip', keyvalue=True)

        def func(conf):
            try:
                client = self.__get_client(conf)
                client.server.list()
            except Exception as ex:
                logger.error(ex, exc_info=1)
                return False
            return True

        configs = self.__get_orchestartors(instances, vip=vip)
        self.run_cmd(func, configs)

    @expose(aliases=[u'ping3 [instances] [vip=true/false]'], aliases_only=True)
    @check_error
    def ping3(self):
        """Ping main components of openstack instances
    - instances: comma separated openstack instances
    - vip: if true query only the vip [default=True]
        """
        instances = self.get_arg(default=None)
        vip = self.get_arg(default=True, name=u'vip', keyvalue=True)

        def func(conf):
            res = {u'keystone': False,
                   u'compute': False,
                   u'block-storage': False,
                   u'object-storage': False,
                   u'network': False,
                   u'orchestrator': False,
                   u'manila': False,
                   u'aodh': False,
                   u'glance': False,
                   u'gnocchi': False}
            try:
                client = self.__get_client(conf)
            except Exception as ex:
                logger.error(ex, exc_info=1)
                return res

            try:
                client.identity.api()
                res[u'keystone'] = True
            except Exception as ex:
                logger.error(ex, exc_info=1)

            try:
                client.system.compute_api()
                res[u'compute'] = True
            except Exception as ex:
                logger.error(ex, exc_info=1)

            try:
                client.system.object_storage_api()
                res[u'object-storage'] = True
            except Exception as ex:
                logger.error(ex, exc_info=1)

            try:
                client.system.storage_api()
                res[u'block-storage'] = True
            except Exception as ex:
                logger.error(ex, exc_info=1)

            try:
                client.system.network_api()
                res[u'network'] = True
            except Exception as ex:
                logger.error(ex, exc_info=1)

            try:
                client.system.orchestrator_api()
                res[u'orchestrator'] = True
            except Exception as ex:
                logger.error(ex, exc_info=1)

            try:
                client.manila.api()
                res[u'manila'] = True
            except Exception as ex:
                logger.error(ex, exc_info=1)

            try:
                client.aodh.api()
                res[u'aodh'] = True
            except Exception as ex:
                logger.error(ex, exc_info=1)

            try:
                client.glance.api()
                res[u'glance'] = True
            except Exception as ex:
                logger.error(ex, exc_info=1)

            try:
                client.gnocchi.api()
                res[u'gnocchi'] = True
            except Exception as ex:
                logger.error(ex, exc_info=1)

            return res

        configs = self.__get_orchestartors(instances, vip=vip)
        self.run_cmd(func, configs)

    @expose(aliases=[u'usage [instances]'], aliases_only=True)
    @check_error
    def usage(self):
        """Displays extra statistical information from the machine that hosts the hypervisor through the API for the
    hypervisor (XenAPI or KVM/libvirt).
    - instances: comma separated openstack instances [optional]
        """
        instances = self.get_arg(default=None)

        configs = self.__get_orchestartors(instances, vip=True)
        resp = []
        for conf in configs:
            client = self.__get_client(conf)

            res = client.system.compute_hypervisors()
            for i in res:
                i[u'instance'] = conf[u'instance']
            resp.extend(res)
        logger.debug('Get openstack hypervisors: %s' % resp)
        self.result(resp, headers=[u'instance', u'id', u'hypervisor_hostname', u'host_ip', u'status', u'state',
                                   u'vcpus', u'vcpus_used', u'memory_mb', u'free_ram_mb', u'local_gb',
                                   u'local_gb_used', u'running_vms'], maxsize=200)

    @expose(aliases=[u'status [instances] [component=..]'], aliases_only=True)
    @check_error
    def status(self):
        """Get services/agents status: compute, storage, network, orchestrator
    - component: openstack component. Can be: compute, storage, network, orchestrator [default=compute]
    - instances: comma separated openstack instances [optional]
        """
        component = self.get_arg(default=u'compute', name=u'component', keyvalue=True)
        instances = self.get_arg(default=None)

        configs = self.__get_orchestartors(instances, vip=True)
        resp = []

        if component == u'compute':
            headers = [u'instance', u'id', u'host', u'zone', u'binary', u'state', u'status', u'updated_at']
        if component == u'network':
            headers = [u'instance', u'id', u'host', u'availability_zone', u'binary', u'agent_type', u'alive',
                       u'started_at']
        if component == u'storage':
            headers = [u'instance', u'id', u'host', u'zone', u'binary', u'state', u'status', u'updated_at']
        if component == u'orchestrator':
            headers = [u'instance', u'id', u'host', u'zone', u'binary', u'state', u'status', u'updated_at']

        for conf in configs:
            client = self.__get_client(conf)

            if component == u'compute':
                res = client.system.compute_services()
            elif component == u'network':
                res = client.system.network_agents()
            elif component == u'storage':
                res = client.system.storage_services()
            elif component == u'orchestrator':
                res = client.system.orchestrator_services()
            else:
                res = []
            for i in res:
                i[u'instance'] = conf[u'instance']
            resp.extend(res)
        logger.debug('Get openstack hypervisors: %s' % resp)
        self.result(resp, headers=headers, maxsize=200)


class NodeController(AnsibleController):
    class Meta:
        label = 'node'
        description = "Nodes management"
    
    def ip_pod_fun(self,pod):
        # range podvc: da 216.141 al 216.159, podto1: dal 152.130 al 152.148, podt2: dal 184.130 al 184.148
        # da 1 a 3: mgmt
        # da 4 a 6: vsphere
        # da 7 a 8: oradb
        # da 9 a 11: osctrl
        # da 12 a 19: kvm

        ip_radice='10.138.'
        ip_pod = list()
        name_pod = list()
        n_nic=list()
        n_nic_up=list()
        if pod == "podvc":   
            for i in range(141,160): ip_pod.append(ip_radice+'216.'+str(i))         
        if pod == "podto1":  
            for i in range(130,149): ip_pod.append(ip_radice+'152.'+str(i))
        if pod == "podto2":  
            for i in range(130,149): ip_pod.append(ip_radice+'184.'+str(i))
        for i in range(1,20):
            if i in (1,2,3):
                name_pod.append(pod+"-mgmt0"+str(i)+'-idrac')
                n_nic.append(6)
                n_nic_up.append(4)
            else: n_nic.append(5)
            if i in (4,5,6):   
                name_pod.append(pod+"-vsphere0"+str(i-3)+'-idrac')
                n_nic.append(6)
                n_nic_up.append(3)
            if i in (7,8):     
                name_pod.append(pod+"-oradb0"+str(i-6)+'-idrac')
                n_nic.append(6)
                n_nic_up.append(3)
            if i in (9,10,11): 
                name_pod.append(pod+"-osctrl0"+str(i-8)+'-idrac')
                n_nic.append(8)
                n_nic_up.append(5)
            if i in (12,13,14,15,16,17,18,19): 
                name_pod.append(pod+"-kvm0"+str(i-11)+'-idrac')
                n_nic.append(8)
                n_nic_up.append(5)
        return([ip_pod,name_pod,n_nic,n_nic_up])
    
    @expose(aliases=[u'power <pod>'], aliases_only=True)
    @check_error
    def power(self):
        """Legge lo stato degli alimentatori di tutto un pod
    da usarsi prima di powervolt    
        """
        pod = self.get_arg(name=u'pod')

        # il presente script interroga via snmp i server dei diversi pod e verifica che non ci siano problemi di alimentazione
        
        conta_errori = 0
                
        community='n1volacommunity'
        value_ps1_status=(1,3,6,1,4,1,674,10892,5,4,600,12,1,5,1,1) # OID che indica se l'alimentatore PS1 ha uno status OK --> ok=3
        value_ps2_status=(1,3,6,1,4,1,674,10892,5,4,600,12,1,5,1,2) # OID che indica se l'alimentatore PS2 ha uno status OK --> ok=3
        
        generator = cmdgen.CommandGenerator()
        comm_data = cmdgen.CommunityData('server', community, 1) # 1 means version SNMP v2c

        l_pod = self.ip_pod_fun(pod)
        ip_pod=l_pod[0]
        name_pod=l_pod[1]
        servers = []
        ind = -1
        for ip in ip_pod:
            ind = ind + 1
            transport = cmdgen.UdpTransportTarget((ip, 161))
            real_fun = getattr(generator, 'getCmd')
            ali = 1
            for value in [value_ps1_status, value_ps2_status]:
                res = (errorIndication, errorStatus, errorIndex, varBinds)\
                    = real_fun(comm_data, transport, value)
                if not errorIndication is None  or errorStatus is True:
                   print "Errore sul server " + ip + ": %s %s %s %s" % res
                else:
                   a = str(varBinds[0])
                   resp_snmp = a.split('= ')[1]
        #       print resp_snmp
        #       print "%s" % varBinds
                   if resp_snmp == "3":
        #               print "server " + ip + " alimentatore n." + str(ali) + " ok: " + resp_snmp
                       if resp_snmp == u'3':
                          resp_snmp = u'OK'
                       servers.append({u'host':name_pod[ind], u'alimentazione':resp_snmp, u'num':str(ali)})
                   else:
                       print "ERRORE --> server " + name_pod(ind) + 'alimentatore n.: ' + str(ali) + " - problemi di alimentazione: " + resp_snmp 
                       conta_errori = conta_errori + 1
                ali = 2
        #    time.sleep(1)
        print "Numero errori rilevati: %s " % conta_errori 
        self.result(servers, headers=[u'host', u'alimentazione', u'num'])
        print "beehive platform node powervolt <pod>  -  per avere indicazioni sui volt in input"


    @expose(aliases=[u'powervolt <pod>'], aliases_only=True)
    @check_error
    def powervolt(self):
        """Legge lo stato della tensione in ingresso per ogni singolo alimentatore
    Da usarsi dopo power per avere indicazioni sui volt in ingresso
        """
        pod = self.get_arg(name=u'pod')

        # il presente script interroga via snmp i server dei diversi pod e raccoglie la tensione su ogni alimentatore 
        conta_errori = 0
        community='n1volacommunity'
        #value=(1,3,6,1,4,1,674,10892,5,2,4,0)
        value_ps1_volt=(1,3,6,1,4,1,674,10892,5,4,600,12,1,16,1,1) # OID che indica il valore dei volt in input sull'alimentatore PS1 
        value_ps2_volt=(1,3,6,1,4,1,674,10892,5,4,600,12,1,16,1,2) # OID che indica il valore dei volt in input sull'alimentatore PS2
        
        generator = cmdgen.CommandGenerator()
        comm_data = cmdgen.CommunityData('server', community, 1) # 1 means version SNMP v2c
        
        l_pod = self.ip_pod_fun(pod)
        ip_pod=l_pod[0]
        name_pod=l_pod[1]
        servers = []
        ind = -1
        for ip in ip_pod:
            ind = ind + 1
            transport = cmdgen.UdpTransportTarget((ip, 161))
            real_fun = getattr(generator, 'getCmd')
            ali = 1
            for value in [value_ps1_volt, value_ps2_volt]:
                res = (errorIndication, errorStatus, errorIndex, varBinds)\
                    = real_fun(comm_data, transport, value)
                if not errorIndication is None  or errorStatus is True:
                   print "Errore sul server " + name_pod[ind] + ": %s %s %s %s" % res
                else:
                   a = str(varBinds[0])
                   resp_snmp = a.split('= ')[1]
                   servers.append({u'host':name_pod[ind], u'volt':resp_snmp, u'num':str(ali)})
                   if resp_snmp == u'No Such Instance currently exists at this OID':
                       print "ERRORE --> server " + name_pod[ind] + ' alimentatore n.: ' + str(ali) + " - problemi di alimentazione: volt a 0" 
                       conta_errori = conta_errori + 1
                ali = 2

        self.result(servers, headers=[u'host', u'volt', u'num'])


    @expose(aliases=[u'memory <pod>'], aliases_only=True)
    @check_error
    def memory(self):
        """Legge lo stato della memoria RAM installata sui server di un pod
    restituisce una stringa di codici per ogni banco di memoria installato:  03 --> ok
        """
        pod = self.get_arg(name=u'pod')

        # il presente script interroga via snmp i server dei diversi pod e raccoglie la tensione su ogni alimentatore 
        print "l'operazione potrebbe durare qualche minuto ..."

        conta_errori = 0
        community='n1volacommunity'
        value_memory=[1,3,6,1,4,1,674,10892,5,4,200,10,1,27,1] # OID che indica lo stato della RAM 3--> OK 
        value_memory_detail=(1,3,6,1,4,1,674,10892,5,4,200,10,1,28,1) # OID che lo stato di ogni banco di ram 3--> OK         
        
        generator = cmdgen.CommandGenerator()
        comm_data = cmdgen.CommunityData('server', community, 1) # 1 means version SNMP v2c
        
        l_pod = self.ip_pod_fun(pod)
        ip_pod=l_pod[0]
        name_pod=l_pod[1]
        servers = []
        ind = -1
        for ip in ip_pod:
            ind = ind + 1
            transport = cmdgen.UdpTransportTarget((ip, 161),timeout=10,retries=0)
            real_fun = getattr(generator, 'getCmd')
            value = value_memory
            res = (errorIndication, errorStatus, errorIndex, varBinds)\
                    = real_fun(comm_data, transport, value)
            if not errorIndication is None  or errorStatus is True:
                   print "Errore sul server " + name_pod[ind] + ": %s %s %s %s" % res
            else:
                   a = str(varBinds[0])
                   resp_snmp = a.split('= ')[1]
                   servers.append({u'host':name_pod[ind], u'stato':resp_snmp})
                   if resp_snmp != "3":
                       print "ERRORE --> server " + name_pod[ind] + " problemi di memoria: " + resp_snmp
                       value = value_memory_detail
                       res = (errorIndication, errorStatus, errorIndex, varBinds)\
                               = real_fun(comm_data, transport, value)
                       if not errorIndication is None  or errorStatus is True:
                            print "Errore sul server " + ip + ": %s %s %s %s" % res
                       else:
                            a = str(varBinds[0])
                            resp_snmp = a.split('= ')[1]
                            print "dettaglio errore di memoria: " + resp_snmp + "\n"
                       conta_errori = conta_errori + 1
        #    time.sleep(1)
        print "Numero errori rilevati: %s " % conta_errori 
        self.result(servers, headers=[u'host', u'stato'])

    @expose(aliases=[u'fans <pod>'], aliases_only=True)
    @check_error
    def fans(self):
        """Legge lo stato delle ventole dei server presensti in un pod
    verifica il funzionamento delle 14 ventole dei server del pod: 03 --> ok
        """
        pod = self.get_arg(name=u'pod')

        # il presente script interroga via snmp i server dei diversi pod e raccoglie lo stato delle 14 ventole  
        print "l'operazione potrebbe durare qualche minuto ..."

        conta_errori = 0
        community='n1volacommunity'
        value_memory_template=[1,3,6,1,4,1,674,10892,5,4,700,12,1,5,1] # OID che indica lo stato di ogni singola ventola (sono 14) 3--> OK 
        
        generator = cmdgen.CommandGenerator()
        comm_data = cmdgen.CommunityData('server', community, 1) # 1 means version SNMP v2c

        l_pod = self.ip_pod_fun(pod)
        ip_pod=l_pod[0]
        name_pod=l_pod[1]
        servers = []
        ind = -1
        for ip in ip_pod:
            ind = ind + 1
            transport = cmdgen.UdpTransportTarget((ip, 161),timeout=10,retries=0)
            real_fun = getattr(generator, 'getCmd')
            for f in range(1,15):
               value = copy.deepcopy(value_memory_template)
               value.append(f)
               res = (errorIndication, errorStatus, errorIndex, varBinds)\
                  = real_fun(comm_data, transport, value)
               if not errorIndication is None  or errorStatus is True:
                   print "Errore sul server " + name_pod[ind] + ": %s %s %s %s" % res
               else:
                   a = str(varBinds[0])
                   resp_snmp = a.split('= ')[1]
                   servers.append({u'host':name_pod[ind], u'ventola':f, u'stato':resp_snmp})
                   if resp_snmp != "3":
                       print "ERRORE --> server " + name_pod[ind] + " problemi su una fun: " + resp_snmp
                       conta_errori = conta_errori + 1
        #    time.sleep(1)
        print "Numero errori rilevati: %s " % conta_errori 
        self.result(servers, headers=[u'host', u'ventola', u'stato'])

    @expose(aliases=[u'disks <pod>'], aliases_only=True)
    @check_error
    def disks(self):
        """Verifica il funzionamento dei dischi fisici dei server del pod: 03 --> ok
        """
        pod = self.get_arg(name=u'pod')
        # il presente script interroga via snmp i server dei diversi pod e raccoglie lo stato delle 14 ventole  
        print "l'operazione potrebbe durare qualche minuto ..."

        conta_errori = 0
        community='n1volacommunity'
        value_memory_template=[1,3,6,1,4,1,674,10892,5,5,1,20,130,4,1,4] # OID che indica lo stato di ogni singola ventola (sono 14) 3--> OK 
        
        generator = cmdgen.CommandGenerator()
        comm_data = cmdgen.CommunityData('server', community, 1) # 1 means version SNMP v2c
        
        l_pod = self.ip_pod_fun(pod)
        ip_pod=l_pod[0]
        name_pod=l_pod[1]
        servers = []
        ind = -1
        for ip in ip_pod:
            ind = ind + 1
            transport = cmdgen.UdpTransportTarget((ip, 161),timeout=10,retries=0)
            real_fun = getattr(generator, 'getCmd')
            for f in range(1,10):
               value = copy.deepcopy(value_memory_template)
               value.append(f)
               res = (errorIndication, errorStatus, errorIndex, varBinds)\
                  = real_fun(comm_data, transport, value)
               if not errorIndication is None  or errorStatus is True:
                   print "Errore sul server " + name_pod[ind] + ": %s %s %s %s" % res
               else:
                   a = str(varBinds[0])
                   resp_snmp = a.split('= ')[1]
                   if resp_snmp == "No Such Instance currently exists at this OID":
                       break
                   servers.append({u'host':name_pod[ind], u'disk':f, u'stato':resp_snmp})
                   if resp_snmp != "3":
                       print "ERRORE --> server " + name_pod[ind] + " problemi su un disco: " + resp_snmp
                       conta_errori = conta_errori + 1
        #    time.sleep(1)
        print "Numero errori rilevati: %s " % conta_errori 
        self.result(servers, headers=[u'host', u'disk', u'stato'])

    @expose(aliases=[u'nics <pod>'], aliases_only=True)
    @check_error
    def nics(self):
        """Verifica il funzionamento delle schede di rete dei server del pod: 03 --> ok
        """
        pod = self.get_arg(name=u'pod')

        # il presente script interroga via snmp i server dei diversi pod e raccoglie lo stato delle schede di rete  
        print "l'operazione potrebbe durare qualche minuto ..."

        conta_errori = 0
        community='n1volacommunity'
        value_memory_template=[1,3,6,1,4,1,674,10892,5,4,1100,90,1,3,1] # OID che indica lo stato di ogni singola ventola (sono 14) 3--> OK 
        
        generator = cmdgen.CommandGenerator()
        comm_data = cmdgen.CommunityData('server', community, 1) # 1 means version SNMP v2c
        
        l_pod = self.ip_pod_fun(pod)
        ip_pod=l_pod[0]
        name_pod=l_pod[1]
        servers = []
        ind = -1
        for ip in ip_pod:
            ind = ind + 1
            transport = cmdgen.UdpTransportTarget((ip, 161),timeout=10,retries=0)
            real_fun = getattr(generator, 'getCmd')
            for f in range(1,10):
               value = copy.deepcopy(value_memory_template)
               value.append(f)
               res = (errorIndication, errorStatus, errorIndex, varBinds)\
                  = real_fun(comm_data, transport, value)
               if not errorIndication is None  or errorStatus is True:
                   print "Errore sul server " + name_pod[ind] + ": %s %s %s %s" % res
               else:
                   a = str(varBinds[0])
                   resp_snmp = a.split('= ')[1]
                   if resp_snmp == "No Such Instance currently exists at this OID":
                       break
                   servers.append({u'host':name_pod[ind], u'nics':f, u'stato':resp_snmp})
                   if resp_snmp != "3":
                       print "ERRORE --> server " + name_pod[ind] + " problemi su un disco: " + resp_snmp
                       conta_errori = conta_errori + 1
        print "Numero errori rilevati: %s " % conta_errori 
        self.result(servers, headers=[u'host', u'nics', u'stato'])


    @expose(aliases=[u'globalstatus <pod>'], aliases_only=True)
    @check_error
    def globalstatus(self):
        """Verifica lo stato globale del sistema dei server del pod: 03 --> ok
        """
        pod = self.get_arg(name=u'pod')
        print "l'operazione potrebbe durare qualche minuto ..."

        conta_errori = 0
        community='n1volacommunity'
        value=[1,3,6,1,4,1,674,10892,5,4,200,10,1,4,1] # OID che indica lo stato di ogni singola ventola (sono 14) 3--> OK 
        
        generator = cmdgen.CommandGenerator()
        comm_data = cmdgen.CommunityData('server', community, 1) # 1 means version SNMP v2c
        
        l_pod = self.ip_pod_fun(pod)
        ip_pod=l_pod[0]
        name_pod=l_pod[1]
        servers = []
        ind = -1
        for ip in ip_pod:
            ind = ind + 1
            transport = cmdgen.UdpTransportTarget((ip, 161),timeout=10,retries=0)
            real_fun = getattr(generator, 'getCmd')
        #    for f in range(1,10):
        #       value = copy.deepcopy(value_memory_template)
        #       value.append(f)
            res = (errorIndication, errorStatus, errorIndex, varBinds)\
                  = real_fun(comm_data, transport, value)
            if not errorIndication is None  or errorStatus is True:
                   print "Errore sul server " + name_pod[ind] + ": %s %s %s %s" % res
            else:
                   a = str(varBinds[0])
                   resp_snmp = a.split('= ')[1]
        #           if resp_snmp == "No Such Instance currently exists at this OID":
        #               break
                   servers.append({u'host':name_pod[ind], u'stato':resp_snmp})
                   if resp_snmp != "3":
                       print "ERRORE --> server " + name_pod[ind] + " problemi generici sul sistema: " + resp_snmp
                       conta_errori = conta_errori + 1
        print "Numero errori rilevati: %s " % conta_errori 
        self.result(servers, headers=[u'host', u'nics', u'stato'])

    @expose(aliases=[u'nicsconnect <pod>'], aliases_only=True)
    @check_error
    def nicsconnect(self):
        """Verifica che il numero di nics connesse sia correto rispetto al desiderata
    mgmt: 4
    vsphere: 3
    oradb: 3
    osctrl: 5
    kvm: 5
        """
        pod = self.get_arg(name=u'pod')

        # il presente script interroga via snmp i server dei diversi pod e raccoglie lo stato delle schede di rete  
        print "l'operazione potrebbe durare qualche minuto ..."

        conta_errori = 0
        community='n1volacommunity'
        value_memory_template=[1,3,6,1,4,1,674,10892,5,4,1100,90,1,4,1] # OID che indica lo stato di ogni singola ventola (sono 14) 3--> OK 
        
        generator = cmdgen.CommandGenerator()
        comm_data = cmdgen.CommunityData('server', community, 1) # 1 means version SNMP v2c
        
        l_pod = self.ip_pod_fun(pod)
        ip_pod=l_pod[0]
        name_pod=l_pod[1]
        n_nic = l_pod[2]
        servers = []
        ind = -1
        for ip in ip_pod:
            ind = ind + 1
            transport = cmdgen.UdpTransportTarget((ip, 161),timeout=10,retries=0)
            real_fun = getattr(generator, 'getCmd')
            conta_up=0
            for f in range(1,10):
               value = copy.deepcopy(value_memory_template)
               value.append(f)
               res = (errorIndication, errorStatus, errorIndex, varBinds)\
                  = real_fun(comm_data, transport, value)
               if not errorIndication is None  or errorStatus is True:
                   print "Errore sul server " + ip + ": %s %s %s %s" % res
               else:
                   a = str(varBinds[0])
                   resp_snmp = a.split('= ')[1]
                   if resp_snmp == "No Such Instance currently exists at this OID":
                       break
                   if resp_snmp == "1":
                       conta_up = conta_up + 1
            if conta_up != l_pod[3][ind]:
                print "ERRORE --> server " + name_pod[ind] + " il numero di porta up non corrisponde al desiderata"
                conta_errori = conta_errori + 1
            servers.append({u'host':name_pod[ind], u'nics':l_pod[3][ind], u'nicsup':conta_up})
        #   print conta_up, l_pod[3][ind]
        #    time.sleep(1)
        print "Numero errori rilevati: %s " % conta_errori 
        self.result(servers, headers=[u'host', u'nics', u'nicsup'])


    def __get_hosts_and_vars(self, env):
        # get environemtn nodes
        try:
            path_inventory = u'%s/inventory/%s' % (self.ansible_path, env)
            path_lib = u'%s/library/beehive/' % (self.ansible_path)
            runner = Runner(inventory=path_inventory, verbosity=self.verbosity, module=path_lib, vault_password=self.vault)
            hosts, hvars = runner.get_inventory_with_vars(u'all')
            hvars = runner.variable_manager.get_vars(runner.loader)
            return hosts, hvars
        except Exception as ex:
            self.error(ex)
            return [], []        

        # get root user
        #vars = runner.variable_manager.get_vars(runner.loader, host=hosts[0])

    @expose()
    @check_error
    def environments(self):
        """List configured environments
        """
        envs = self.configs[u'environments']
        default = envs.pop(u'default')
        resp = []
        for e in envs.keys():
            hosts, hvars = self.__get_hosts_and_vars(e)
            resp.append({u'environment': e, u'hosts': hosts})
        logger.debug(resp)
        self.app.print_output(u'Default environment: %s' % default)
        self.result(resp, headers=[u'environment', u'hosts'], maxsize=400)
    
    @expose(aliases=[u'list <group>'], aliases_only=True)
    @check_error
    def list(self):
        """List managed platform nodes
        """
        group = self.get_arg(default=None)
        self.ansible_inventory(group)
        
    @expose(aliases=[u'create <group>'], aliases_only=True)
    @check_error
    def create(self):
        """Create group nodes
        """
        group = self.get_arg(default=u'all')
        run_data = {
            u'tags':[u'create']
        }        
        self.ansible_playbook(group, run_data, playbook=self.create_playbook)

    @expose(aliases=[u'update <group>'], aliases_only=True)
    @check_error
    def update(self):
        """Update group nodes - change hardware configuration
        """
        group = self.get_arg(default=u'all')
        run_data = {
            u'tags':[u'update']
        }        
        self.ansible_playbook(group, run_data, playbook=self.site_playbook)

    @expose(aliases=[u'configure <group>'], aliases_only=True)
    @check_error
    def configure(self):
        """Make main configuration on group nodes
        """
        group = self.get_arg(default=u'all')
        run_data = {
            u'tags':[u'configure']
        }        
        self.ansible_playbook(group, run_data,playbook=self.site_playbook)
        
    @expose(aliases=[u'ssh-copy-id <group>'], aliases_only=True)
    @check_error
    def ssh_copy_id(self):
        """Copy ssh id on group nodes
        """
        group = self.get_arg(default=u'all')
        run_data = {
            u'tags':[u'ssh']
        }        
        self.ansible_playbook(group, run_data, playbook=self.site_playbook)
        
    @expose(aliases=[u'install <group>'], aliases_only=True)
    @check_error
    def install(self):
        """Install software on group nodes
        """
        group = self.get_arg(default=u'all')
        if group == u'all':
            playbook = self.site_playbook
        else:
            playbook = u'%s/%s.yml' % (self.ansible_path, group)
        run_data = {
            u'tags': [u'install']
        }        
        self.ansible_playbook(group, run_data, playbook=playbook)

    @expose(aliases=[u'hosts <group>'], aliases_only=True)
    @check_error
    def hosts(self):
        """Configure nodes hosts local resolution
        """
        group = self.get_arg(default=u'all')
        run_data = {
            u'tags': [u'hosts']
        }        
        self.ansible_playbook(group, run_data, playbook=self.site_playbook)
        
    @expose(aliases=[u'cmd <group> <cmd>'], aliases_only=True)
    @check_error
    def cmd(self):
        """Execute command on managed platform nodes
    - group: ansible group
    - cmd: shell command   
        """
        group = self.get_arg(name=u'group')
        cmd  = self.get_arg(name=u'cmd')     
        path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
        path_lib = u'%s/library/beehive/' % (self.ansible_path)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity, module=path_lib, vault_password=self.vault)
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
                res = {u'vassals': None, u'blacklist': None}
        else:
            logger.error(u'Emperor %s does not respond' % server)
            res = u'Emperor %s does not respond' % server
        return res

    def __get_uwsgi_tree(self, group):
        """
        """
        '''path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
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
        hosts = self.get_multi_hosts(system)

        '''path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
        hosts = runner.get_inventory(group=system)'''

        resp = []
        for host in hosts:
            host = str(host)
            res = self.__get_stats(host)
            vassals = res.pop(u'vassals')
            res.pop(u'blacklist')
            try:
                temp = [u'%s [%s]' % (v[u'id'].replace(u'/etc/uwsgi/vassals/', u'').replace(u'.ini', u''), v[u'pid'])
                        for v in vassals]
                res[u'vassals'] = u', '.join(temp)
            except:
                res[u'vassals'] = []
            res[u'host'] = host
            resp.append(res)
        self.result(resp, headers=[u'host', u'pid', u'version', u'uid', u'gid', u'throttle_level', u'emperor_tyrant',
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
            hosts = self.get_multi_hosts(system)

            '''path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
            runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
            hosts = runner.get_inventory(group=system)'''

            resp = []
            for host in hosts:
                host = str(host)
                res = self.__get_stats(host)
                vassals = res.pop(u'vassals')
                for vassal in vassals or []:
                    vassal[u'id'] = vassal[u'id'].replace(u'/etc/uwsgi/vassals/', u'').replace(u'.ini', u'')
                    vassal.update({u'host':host})
                    for key in [u'first_run', u'last_run', u'last_ready', 
                                u'last_mod', u'last_accepting']:
                        vassal[key] = self.cdate(vassal[key])
                    resp.append(vassal)
    
            self.result(resp, headers=[u'host', u'pid', u'uid', u'gid', u'id', u'first_run', u'last_run', u'last_ready',
                                       u'last_mod', u'last_accepting'])
        except Exception as ex:
            self.error(ex)            
                            
    def get_emperor_blacklist(self, details=u'', system=None):
        """Get uwsgi emperor active vassals statistics
        
        :param server: host name
        """
        hosts = self.get_multi_hosts(system)

        '''path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity)
        hosts = runner.get_inventory(group=system)'''

        for host in hosts:
            host = str(host)
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
    def get_job_state(self, jobid):
        try:
            res = self._call(u'/v1.0/nrs/worker/tasks/%s' % jobid, u'GET')
            state = res.get(u'task_instance').get(u'status')
            logger.debug(u'Get job %s state: %s' % (jobid, state))
            if state == u'FAILURE':
                # print(res)
                self.app.print_error(res[u'task_instance'][u'traceback'][-1])
                self.app.error = False
            return state
        except (Exception):
            return u'EXPUNGED'

    def wait_job(self, jobid, delta=1):
        """Wait resource
        """
        logger.debug(u'wait for job: %s' % jobid)
        state = self.get_job_state(jobid)
        while state not in [u'SUCCESS', u'FAILURE']:
            logger.info(u'.')
            print(u'.')
            sleep(delta)
            state = self.get_job_state(jobid)

    @expose(aliases=[u'post-install <config>'], aliases_only=True)
    @check_error
    def post_install(self):
        """
        """
        # get configs
        all_configs = self.load_config(self.get_arg(name=u'config'))
        apply = all_configs.get(u'apply')
        configs = all_configs.get(u'configs')

        self.subsystem = u'auth'

        # oauth2 scopes
        if apply.get(u'oauth2', False) is True:
            for scope in configs.get(u'oauth2').get(u'scopes'):
                res = self._call(u'/v1.0/oauth2/scopes', u'POST', data={u'scope': scope})
                logger.info(u'Add scope: %s' % res)
                self.output(u'Add scope: %s' % scope)

        # auth roles, users and groups
        if apply.get(u'auth', False) is True:
            for obj in configs.get(u'auth').get(u'roles'):
                res = self._call(u'/v1.0/nas/roles', u'POST', data={u'role': {u'name': obj, u'desc': obj}})
                logger.info(u'Add role: %s' % res)
                self.output(u'Add roles: %s' % obj)
            # TODO: users
            # TODO: groups

        # auth and catalog objects and schedule
        if apply.get(u'auth-schedule', False) is True:
            for schedule in configs.get(u'auth').get(u'schedules'):
                res = self._call(u'/v1.0/nas/scheduler/entries', u'POST', data={u'schedule': schedule})
                logger.info(u'Add schedule: %s' % res)
                self.output(u'Add schedule: %s' % scope)

        # camunda
        # - metatabelle decisioni
        # - processi

        self.subsystem = u'resource'

        # resource tags
        if apply.get(u'resource-tags', False) is True:
            for obj in configs.get(u'resource').get(u'tags'):
                try:
                    res = self._call(u'/v1.0/nrs/tags', u'POST', data={u'resourcetag': {u'value': obj}})
                    logger.info(u'Add tag: %s' % res)
                    self.output(u'Add tag: %s' % obj)
                except Exception as ex:
                    self.error(ex)
                    self.app.error = False

        # resource containers
        if apply.get(u'resource-containers', False) is True:
            for obj in configs.get(u'resource').get(u'containers'):
                try:
                    res = self._call(u'/v1.0/nrs/containers', u'POST', data={u'resourcecontainer': obj})
                    logger.info(u'Add container: %s' % res)
                    self.output(u'Add container: %s' % obj)
                except Exception as ex:
                    self.error(ex)
                    self.app.error = False

        # resource containers sync
        if apply.get(u'resource-containers-sync', False) is True:
            for obj in configs.get(u'resource').get(u'containers'):
                name = obj.get(u'name')
                cont_type = obj.get(u'type')
                for type in configs.get(u'resource').get(u'container_type').get(cont_type, []):
                    res = self._call(u'/v1.0/nrs/containers/%s/discover' % name, u'PUT',
                                     data={u'synchronize': {
                                          u'types': type, u'new': True, u'died': False, u'changed': False}})
                    self.wait_job(res[u'jobid'], delta=1)
                    logger.info(u'Sync container %s type %s' % (name, type))
                    self.output(u'Sync container %s type %s' % (name, type))

        # resource entities
        if apply.get(u'resource-entities', False) is True:
            entitie_types = [u'region', u'site', u'site_network', u'compute_zone', u'image', u'flavor']
            for entitie_type in entitie_types:
                resources = configs.get(u'resource').get(u'entities')
                for obj in resources.get(entitie_type+u's'):
                    try:
                        res = self._call(u'/v1.0/nrs/provider/'+entitie_type+u's', u'POST', data={entitie_type: obj})
                        if u'jobid' in res:
                            self.wait_job(res[u'jobid'], delta=1)
                        logger.info(u'Add %s: %s' % (entitie_type, res))
                        self.output(u'Add %s: %s' % (entitie_type, obj))
                    except Exception as ex:
                        self.error(ex)
                        self.app.error = False

                    if entitie_type == u'site':
                        for orc in resources.get(u'site_orchestrators').get(obj[u'name']):
                            try:
                                if orc[u'type'] == u'openstack':
                                    # get domain
                                    data = urllib.urlencode({u'container': orc[u'id'], u'name': u'Default'})
                                    domain = self._call(u'/v1.0/nrs/openstack/domains', u'GET', data=data)
                                    orc[u'config'][u'domain'] = domain[u'domains'][0][u'id']
                                res = self._call(u'/v1.0/nrs/provider/sites/%s/orchestrators' % obj[u'name'], u'POST',
                                                 data={u'orchestrator': orc})
                                self.wait_job(res[u'jobid'], delta=1)
                                logger.info(u'Add site %s orchestrator: %s' % (obj.get(u'name'), res))
                                self.output(u'Add site %s orchestrator: %s' % (obj.get(u'name'), orc))
                            except Exception as ex:
                                self.error(ex)
                                self.app.error = False

                    if entitie_type == u'compute_zone':
                        name = obj.get(u'name')
                        quota = obj.get(u'quota')
                        sites = obj.get(u'sites')
                        for site in sites:
                            try:
                                res = self._call(u'/v1.0/nrs/provider/compute_zones/%s/sites' % name, u'POST',
                                                 data={u'site': {u'id': site,
                                                                 u'orchestrator_tag': u'default',
                                                                 u'quota': quota}})
                                self.wait_job(res[u'jobid'], delta=1)
                                logger.info(u'Add compute_zone site: %s' % res)
                                self.output(u'Add compute_zone site: %s' % site)
                            except Exception as ex:
                                self.error(ex)
                                self.app.error = False

        self.subsystem = u'service'

        # create service types
        if apply.get(u'service-types', False) is True:
            for obj in configs.get(u'service').get(u'types'):
                res = self._call(u'/v1.0/nws/servicetypes', u'POST', data={u'servicetype': obj})
                logger.info(u'Add service type: %s' % res)
                self.output(u'Add service type: %s' % obj)

        # create service defs
        if apply.get(u'service-defs', False) is True:
            for obj in configs.get(u'service').get(u'defs'):
                try:
                    configs = obj.pop(u'configs')
                    res = self._call(u'/v1.0/nws/servicedefs', u'POST', data={u'servicedef': obj})
                    logger.info(u'Add service def: %s' % res)
                    self.output(u'Add service def: %s' % obj)

                    data = {
                        u'name': u'%s-config' % obj.get(u'name'),
                        u'desc': u'%s-config' % obj.get(u'name'),
                        u'service_definition_id': res[u'uuid'],
                        u'params': configs,
                        u'params_type': u'JSON',
                        u'version': obj.get(u'version')
                    }
                    res = self._call(u'/v1.0/nws/servicecfgs', u'POST', data={u'servicecfg': data})
                    logger.info(u'Add service def config: %s' % res)
                    self.output(u'Add service def config: %s' % configs)
                except Exception as ex:
                    self.error(ex)
                    self.app.error = False

        # create service catalogs
        if apply.get(u'service-catalogs', False) is True:
            for obj in configs.get(u'service').get(u'catalogs'):
                try:
                    name = obj.get(u'name')
                    defs = obj.get(u'defs')
                    res = self._call(u'/v1.0/nws/srvcatalogs', u'POST', data={u'catalog': {u'name': name, u'desc': name}})
                    logger.info(u'Add service catalog: %s' % res)
                    self.output(u'Add service catalog: %s' % obj)
                except Exception as ex:
                    self.error(ex)
                    self.app.error = False

                res = self._call(u'/v1.0/nws/srvcatalogs/%s/defs' % res[u'uuid'], u'PUT',
                                 data={u'definitions': {u'oids': defs}})
                logger.info(u'Add service catalog defs: %s' % res)
                self.output(u'Add service catalog defs: %s' % defs)

        # create main org structure
        # org, div, account common

    @expose()
    @check_error
    def sync(self):
        """Sync beehive package an all nodes with remove git repository
        """
        run_data = {
            u'tags': [u'sync']
        }        
        self.ansible_playbook(u'beehive', run_data, playbook=self.beehive_playbook)
    
    @expose()
    @check_error
    def pip(self):
        """Sync beehive package an all nodes with remove git repository
        """
        run_data = {
            u'tags': [u'pip']
        }        
        self.ansible_playbook(u'beehive', run_data, playbook=self.beehive_playbook)
    
    @expose()
    @check_error
    def subsystems(self):
        """List beehive subsystems
        """        
        self.get_emperor_nodes_stats(u'beehive')    
    
    @expose(aliases=[u'subsystem-create <subsystem>'], aliases_only=True)
    @check_error
    def subsystem_create(self):
        """Create beehive subsystem
    - subsystem: subsystem
        """
        subsystem = self.get_arg(name=u'subsystem')
        run_data = {
            u'subsystem': subsystem,
            u'tags': [u'subsystem']
        }        
        self.ansible_playbook(u'beehive-init', run_data, playbook=self.beehive_playbook)
    
    @expose(aliases=[u'subsystem-update <subsystem>'], aliases_only=True)
    @check_error
    def subsystem_update(self):
        """Create beehive subsystem
    - subsystem: subsystem
        """
        subsystem = self.get_arg(name=u'subsystem')
        run_data = {
            u'subsystem': subsystem,
            u'tags': [u'subsystem'],
            u'create': False,
            u'update': True
        }
        self.ansible_playbook(u'beehive-init', run_data, playbook=self.beehive_playbook)
    
    @expose(aliases=[u'instances [details=""]'], aliases_only=True)
    @check_error
    def instances(self):
        """List beehive subsystem instances
    - details: if True print details
        """
        details = self.get_arg(default=u'')  
        self.get_emperor_vassals(details, u'beehive')    
    
    @expose(aliases=[u'blacklist [details=""]'], aliases_only=True)
    @check_error
    def blacklist(self):
        """List beehive subsystem instances blacklist
    - details: if True print details
        """
        details = self.get_arg(default=u'')         
        self.get_emperor_blacklist(details, u'beehive')    
    
    @expose(aliases=[u'instance-sync <subsystem> <vassal>'], aliases_only=True)
    @check_error
    def instance_sync(self):
        """Sync beehive package an all nodes with local git repository and
        restart instances
    - subsystem: subsystem
    - vassal: vassal
        """
        subsystem = self.get_arg(name=u'subsystem')
        vassal = self.get_arg(name=u'vassal')
        run_data = {
            u'local_package_path': self.local_package_path,
            u'subsystem': subsystem,
            u'vassal': u'%s-%s' % (subsystem, vassal),
            u'tags': [u'sync-dev']
        }        
        self.ansible_playbook(u'beehive', run_data, playbook=self.beehive_playbook)
    
    @expose(aliases=[u'instance-deploy <subsystem> <vassal>'], aliases_only=True)
    @check_error
    def instance_deploy(self):
        """Deploy beehive instance for subsystem
    - subsystem: subsystem
    - vassal: vassal
        """
        subsystem = self.get_arg(name=u'subsystem')
        vassal = self.get_arg(name=u'vassal')
        run_data = {
            u'subsystem': subsystem,
            u'vassal': u'%s-%s' % (subsystem, vassal),
            u'tags': [u'deploy']
        }        
        self.ansible_playbook(u'beehive', run_data, playbook=self.beehive_playbook)
    
    @expose(aliases=[u'instance-undeploy <subsystem> <vassal>'], aliases_only=True)
    @check_error
    def instance_undeploy(self):
        """Undeploy beehive instance for subsystem
    - subsystem: subsystem
    - vassal: vassal
        """
        subsystem = self.get_arg(name=u'subsystem')
        vassal = self.get_arg(name=u'vassal')
        run_data = {
            u'subsystem': subsystem,
            u'vassal': u'%s-%s' % (subsystem, vassal),
            u'tags': [u'undeploy']
        }        
        self.ansible_playbook(u'beehive', run_data, playbook=self.beehive_playbook)
    
    @expose(aliases=[u'instance-ping [subsystem] [vassal]'], aliases_only=True)
    @check_error
    def instance_ping(self):
        """Ping beehive instance
    - subsystem: subsystem
    - vassal: vassal
        """
        subsystem = self.get_arg()
        vassal = self.get_arg()
        '''path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
        path_lib = u'%s/library/beehive/' % (self.ansible_path)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity, module=path_lib, vault_password=self.vault)
        hosts, vars = runner.get_inventory_with_vars(u'beehive')
        vars = runner.variable_manager.get_vars(runner.loader, host=hosts[0])'''

        runners = self.get_runners()
        hosts = []
        for runner in runners:
            hosts.extend(self.get_hosts(runner, [u'beehive']))
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
                http = HTTPClient(url.host, port=url.port, headers={u'Content-Type': u'application/json'})
                try:
                    # issue a get request
                    response = http.get(url.request_uri)
                    # read status_code
                    response.status_code
                    # read response body
                    # res = json.loads(response.read())
                    # close connections
                    http.close()
                    if response.status_code == 200:
                        resp.append({u'subsystem': vassal[0], u'instance': vassal[1], u'host': host, u'port': port,
                                     u'ping': True, u'status': u'UP'})
                    else:
                        resp.append({u'subsystem': vassal[0], u'instance': vassal[1], u'host': host, u'port': port,
                                     u'ping': False, u'status': u'DOWN'})
                except gevent.socket.error as ex:
                    logger.error(ex)
                    resp.append({u'subsystem': vassal[0], u'instance': vassal[1], u'host': host, u'port': port,
                                 u'ping': False, u'status': u'DOWN'})
                except Exception as ex:
                    logger.error(ex)
                    resp.append({u'subsystem': vassal[0], u'instance': vassal[1], u'host': host, u'port': port,
                                 u'ping': False, u'status': u'DOWN'})

        self.result(resp, headers=[u'subsystem', u'instance', u'host', u'port', u'status'])
        
    @expose(aliases=[u'instance-log <subsystem> <vassal> [rows=100]'], aliases_only=True)
    @check_error
    def instance_log(self):
        """Get instance log
    - subsystem: beehive subsystem. Ex. auth, event
    - vassal: instance number. Ex. 01
    - rows: number of row to tail [default=100]
        """
        group = u'beehive'
        subsystem = self.get_arg(name=u'subsystem')
        vassal = self.get_arg(name=u'vassal')
        rows = self.get_arg(default=100)
        cmd  = u'tail -%s /var/log/beehive/beehive100/%s-%s.log' % (rows, subsystem, vassal)
        path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
        path_lib = u'%s/library/beehive/' % (self.ansible_path)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity, 
                        module=path_lib, vault_password=self.vault)
        tasks = [
            dict(action=dict(module=u'shell', args=cmd), register=u'shell_out'),
        ]
        runner.run_task(group, tasks=tasks, frmt=u'text')
                
    @expose(aliases=[u'uwsgi-log <subsystem> <vassal> [rows=100]'], aliases_only=True)
    @check_error
    def uwsgi_log(self):
        """Get uwsgi instance log
    - subsystem: beehive subsystem. Ex. auth, event
    - vassal: instance number. Ex. 01
    - rows: number of row to tail [default=100] 
        """
        group = u'beehive'
        subsystem = self.get_arg(name=u'subsystem')
        vassal = self.get_arg(name=u'vassal')
        rows = self.get_arg(default=100)
        cmd  = u'tail -%s /var/log/beehive/beehive100/%s-%s.uwsgi.log' % \
            (rows, subsystem, vassal)
        path_inventory = u'%s/inventory/%s' % (self.ansible_path, self.env)
        path_lib = u'%s/library/beehive/' % (self.ansible_path)
        runner = Runner(inventory=path_inventory, verbosity=self.verbosity, 
                        module=path_lib, vault_password=self.vault)
        tasks = [
            dict(action=dict(module=u'shell', args=cmd), register=u'shell_out'),
        ]
        runner.run_task(group, tasks=tasks, frmt=u'text')                
                
    '''def beehive_get_uwsgi_tree(self):
        """
        """
        self.__get_uwsgi_tree(self.env, u'beehive')'''
    
    @expose()
    @check_error
    def doc(self):
        """Make e deploy beehive documentation
        """
        run_data = {
            u'tags': [u'doc'],
            u'local_package_path': self.local_package_path
        }        
        self.ansible_playbook(u'docs', run_data, playbook=self.beehive_doc_playbook)

    @expose()
    @check_error
    def apidoc(self):
        """Make e deploy beehive api documentation
        """
        run_data = {
            u'tags': [u'apidoc'],
            u'local_package_path': self.local_package_path
        }
        self.ansible_playbook(u'docs', run_data, playbook=self.beehive_doc_playbook)


platform_controller_handlers = [
    PlatformController,
    NginxController,
    RedisController,
    RedisClutserController,
    MysqlController,
    CamundaController,
    CamundaDeployController,
    CamundaProcessController,
    VsphereController,
    OpenstackController,
    NodeController,
    BeehiveController,
]
