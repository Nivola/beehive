'''
Created on Jan 9, 2017

@author: darkbk
'''
import ujson as json
from beecell.db.manager import RedisManager, MysqlManager
from geventhttpclient import HTTPClient
from geventhttpclient.url import URL

def test_redis(server, port=6379):
    """Test redis instance
    
    :param server: host name
    :param port: server port [default=6379]
    """
    redis_uri = '%s;%s;1' % (server, port)
    server = RedisManager(redis_uri)
    res = server.ping()
    print('Ping redis %s : %s' % (redis_uri, res))
    #info = server.info()
    #for k,v in info.items():
    #    print('%-30s : %-20s' % (k,v))
        
def test_mysql(server, user, pwd, db, port=3306):
    """Test redis instance
    
    :param server: host name
    :param port: server port [default=6379]
    """
    db_uri = 'mysql+pymysql://%s:%s@%s:%s/%s' % (user, pwd, server, port, db)
    server = MysqlManager(1, db_uri)
    server.create_simple_engine()
    res = server.ping()
    print('Ping mysql %s : %s' % (db_uri, res))

def test_beehive(server, port):
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
    print('Ping beehive %s : %s' % (url.request_uri, resp))