'''
Created on Aug 11, 2017

@author: darkbk
'''
import flex
import requests
from requests.auth import HTTPBasicAuth
import pprint
from beecell.swagger import ApiValidator
from flex.core import load

pp = pprint.PrettyPrinter(indent=4)

schema_uri = u'http://10.102.184.52:6090/apispec_1.json'

#resp = requests.get(uri)
#data = resp.json()

schema = load(schema_uri)

uri_template = u'/v1.0/resourcecontainers/{oid}'
method = u'get'
response = requests.get(u'http://10.102.184.52:6090/v1.0/resourcecontainers/test-container', 
                        auth=HTTPBasicAuth(u'admin@local', u'testlab'))
#response = requests.get(u'http://10.102.184.52:6060/v1.0/auth/users/10', 
#                       auth=HTTPBasicAuth(u'admin1@local', u'testlab'))
code = str(response.status_code)
pp.pprint(response.json())

val = ApiValidator(schema, uri_template, method)
res = val.validate(response)
print res

    