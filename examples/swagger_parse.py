'''
Created on Aug 11, 2017

@author: darkbk
'''
from swagger_parser import SwaggerParser
import requests
import pprint
pp = pprint.PrettyPrinter(indent=4)

uri = u'http://10.102.184.52:6060/apispec_1.json'

resp = requests.get(uri)
data = resp.json()

parser = SwaggerParser(swagger_dict=data)  # Init with dictionary

pp.pprint(parser.get_path_spec(u'/v1.0/auth/users'))
print parser.get_send_request_correct_body(u'/v1.0/auth/users', u'get')
print parser.get_request_data(u'/v1.0/auth/users', u'get').get(200)

print parser.validate_request(u'/v1.0/auth/users', u'get', query={u'user1':u''})