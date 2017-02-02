'''
Created on Jan 9, 2017

@author: darkbk
'''
import logging
import ujson as json
from beecell.db.manager import RedisManager, MysqlManager
from geventhttpclient import HTTPClient
from geventhttpclient.url import URL

logger = logging.getLogger(__name__)

class PlatformManager(object):
    def __init__(self, auth_config):
        self.baseuri = u'/v1.0/resource'
        self.subsystem = u'resource'
        self.logger = logger
        self.msg = None
    
    def actions(self):
        actions = {
            u'redis.test': self.test_redis,
            u'mysql.test': self.test_mysql,
            u'beehive.test': self.test_beehive,
            u'emperor.stats': self.get_emperor_stats,
            u'emperor.vassals': self.get_emperor_vassals,

        }
        return actions    
    
    #
    # resource containers
    #
    def get_resource_containers(self, tags=None):
        uri = u'%s/containers/' % self.baseuri
        if tags is not None:
            headers = {u'tags':tags}
        else:
            headers = None
        res = self._call(uri, u'GET', headers=headers)
        self.logger.info(u'Get resource containers: %s' % res)
        self.msg = res[u'containers']
        return res

    def test_redis(self, server, port=6379):
        """Test redis instance
        
        :param server: host name
        :param port: server port [default=6379]
        """
        redis_uri = '%s;%s;1' % (server, port)
        server = RedisManager(redis_uri)
        res = server.ping()
        self.logger.info(u'Ping redis %s : %s' % (redis_uri, res))
        self.msg = u'Ping redis %s : %s' % (redis_uri, res)
            
    def test_mysql(self, server, user, pwd, db, port=3306):
        """Test redis instance
        
        :param server: host name
        :param port: server port [default=6379]
        """
        db_uri = 'mysql+pymysql://%s:%s@%s:%s/%s' % (user, pwd, server, port, db)
        server = MysqlManager(1, db_uri)
        server.create_simple_engine()
        res = server.ping()
        self.logger.info(u'Ping mysql %s : %s' % (db_uri, res))
        self.msg = u'Ping mysql %s : %s' % (db_uri, res)
    
    def test_beehive(self, server, port):
        """Test redis instance
        
        :param server: host name
        :param port: server port [default=6379]
        """
        url = URL('http://%s:%s/v1.0/server/ping/' % (server, port))
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
        self.msg = u'Ping beehive %s : %s' % (url.request_uri, resp)
        
    def get_emperor_stats(self, server):
        """Get uwsgi emperor statistics
        
        :param server: host name
        """
        url = URL(u'http://%s:%s/' % (server, 80))
        print url.request_uri
        http = HTTPClient(url.host, port=80)
        # issue a get request
        response = http.get(url.request_uri)
        # read status_code
        response.status_code
        # read response body
        res = json.loads(response.read())
        # close connections
        http.close()
        if res[u'status'] == u'ok':
            res.pop(u'vassals')
            res.pop(u'blacklist')
            self.logger.info(res)
            self.logger.info(res)
            self.msg = res
        else:
            self.logger.error(u'Emperor %s does not respond' % server)
            self.msg = u'Emperor %s does not respond' % server
        
    def get_emperor_vassals(self, server):
        """Get uwsgi emperor active vassals statistics
        
        :param server: host name
        """
        url = URL('http://%s:%s/' % (server, 80))
        http = HTTPClient(url.host, port=80)
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
        self.msg = u'Ping beehive %s : %s' % (url.request_uri, resp)
    
def platform_main(auth_config, format, opts, args):
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
    
    client = PlatformManager(auth_config)
    
    actions = client.actions()
    
    entity = args.pop(0)
    if len(args) > 0:
        operation = args.pop(0)
        action = u'%s.%s' % (entity, operation)
    else: 
        raise Exception(u'Platform entity and/or command are not correct')
        return 1
    
    if action is not None and action in actions.keys():
        func = actions[action]
        res = func(*args)
    else:
        raise Exception(u'Platform entity and/or command are not correct')
        return 1
            
    if format == u'text':
        for i in res:
            pass
    else:
        print(u'Platform response:')
        print(u'')
        if isinstance(client.msg, dict) or isinstance(client.msg, list):
            client.pp.pprint(client.msg)
        else:
            print(client.msg)
        
    return 0    