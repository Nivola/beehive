'''
Created on Aug 11, 2017

@author: io
'''
import flex
import requests
from requests.auth import HTTPBasicAuth
import pprint
from beecell.swagger import ApiValidator
from flex.core import load

pp = pprint.PrettyPrinter(indent=4)

schema = None
baseuri = u'http://10.102.184.52:6060'
user = u'admin@local'
pwd = u'testlab'

def call(uri_template, method, params={}, user=None, pwd=None):
    global baseuri
    auth = None
    uri = uri_template.format(**params)
    print(u'Request uri: %s' % uri)
    if user is not None:
        auth = HTTPBasicAuth(user, pwd)
    response = requests.get(baseuri + uri, auth=auth)
    print(u'Response code: %s' % response.status_code)
    print(u'Response')
    pp.pprint(response.json())
    
    val = ApiValidator(schema, uri_template, method)
    res = val.validate(response)
    print res
    
def setup_module(module):
    global schema
    schema_uri = u'%s/apispec_1.json' % baseuri
    schema = load(schema_uri)
    print (u'Load swagger schema from %s' % schema_uri)
    print()
 
def teardown_module(module):
    pass
 
def setup_function(function):
    print (u'--------- %s ---------' % function.__name__)
 
def teardown_function(function):
    print (u'--------- %s ---------' % function.__name__)

'''
def test_get_domains():
    global user, pwd
    call(u'/v1.0/auth/domains', u'get')
'''

def test_get_users():
    global user, pwd
    call(u'/v1.0/auth/users', u'get', {}, user, pwd)
    
def test_get_user():
    global user, pwd
    call(u'/v1.0/auth/users/{oid}', u'get', {u'oid':4}, user, pwd)    
    
    
    