'''
Created on Aug 11, 2017

@author: darkbk
'''
# from swagger_parser import SwaggerParser
# import requests
# import pprint
# pp = pprint.PrettyPrinter(indent=4)
# 
# uri = u'http://10.102.184.52:6060/apispec_1.json'
# 
# resp = requests.get(uri)
# data = resp.json()
# 
# parser = SwaggerParser(swagger_dict=data)  # Init with dictionary
# 
# pp.pprint(parser.get_path_spec(u'/v1.0/auth/users'))
# print parser.get_send_request_correct_body(u'/v1.0/auth/users', u'get')
# print parser.get_request_data(u'/v1.0/auth/users', u'get').get(200)
# 
# print parser.validate_request(u'/v1.0/auth/users', u'get', query={u'user1':u''})
from marshmallow.schema import Schema
from marshmallow import fields, missing

from apispec import APISpec
from marshmallow.validate import Range, OneOf
from beecell.swagger import SwaggerHelper
from pprint import pprint
from marshmallow.exceptions import ValidationError

# spec = APISpec(
#     title='',
#     version='',
#     plugins=[
#         'apispec.ext.flask',
#         'apispec.ext.marshmallow'
#     ]
# )

class PaginatedRequestQuerySchema(Schema):
    size = fields.Integer(default=10, context=u'path',
                          validate=Range(min=0, max=200,
                                         error=u'Size is out from range'))
    page = fields.Integer(default=0, context=u'path',
                          validate=Range(min=0, max=1000,
                                         error=u'Page is out from range'))
    order = fields.String(validate=OneOf([u'ASC', u'asc', u'DESC', u'desc'],
                                         error=u'Order can be asc, ASC, desc, DESC'),
                          default=u'DESC', context=u'path')
    field = fields.String(validate=OneOf([u'id', u'uuid', u'objid', u'name'],
                                         error=u'Field can be id, uuid, objid, name'),
                          default=u'id', context=u'path')

class UsersRequestQuerySchema(PaginatedRequestQuerySchema):
    group = fields.String(description='Filter user by group')
    role = fields.String(context=u'query')
    active = fields.Boolean()
    expiry_date = fields.Date(load_from=u'expiry-date')
    
class CreateUserParamRequestSchema(Schema):
    password = fields.String(error=u'Password must be at least 8 characters')
    storetype = fields.String(validate=OneOf([u'DBUSER', u'LDAPUSER', u'SPID'],
                          error=u'Field can be DBUSER, LDAPUSER or SPIDUSER'),
                          missing=u'DBUSER')
    base = fields.Boolean(missing=True)
    system = fields.Boolean()


class CreateUserRequestSchema(Schema):
    user = fields.Nested(CreateUserParamRequestSchema)
    
class UpdateUserBodyRequestSchema(Schema):
    oid = fields.String(context=u'query')
    body = fields.Nested(CreateUserRequestSchema, context=u'body')    

'''
spec.definition('users', schema=UsersRequestQuerySchema)


fields = UsersRequestQuerySchema.__dict__.get(u'_declared_fields', [])

for field, value in fields.items():
    kvargs = {
        'reuqired':value.required, 
        'description':value.metadata.get(u'description', u''),
    }    
    field_type = value.__class__.__name__.lower()
    field_format = None
    if field_type == u'date':
        kvargs['type'] = u'string'
        kvargs['format'] = u'date'
    else:
        kvargs['type'] = field_type
    if bool(value.default) is not False:
        kvargs['default'] = value.default
    if value.load_from is not None:
        field = value.load_from
    if value.validate is not None and isinstance(value.validate, OneOf):
        print value.validate.choices
        kvargs['enum'] = value.validate.choices

    spec.add_parameter(field, u'query', **kvargs)'''
    
spec = SwaggerHelper()

pprint(SwaggerHelper().get_parameters(UpdateUserBodyRequestSchema))
        