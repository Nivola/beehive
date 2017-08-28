'''
Created on Aug 9, 2017

@author: darkbk
'''
from beehive.common.test import runtest, BeehiveTestCase, assert_exception
from beecell.remote import BadRequestException, NotFoundException,\
    UnauthorizedException

tests = [
    u'test_create_token',
#     u'test_create_token_wrong_user_syntax',
#     u'test_create_token_wrong_user',
#     u'test_create_token_wrong_pwd',
#     u'test_create_token_no_user',
#     u'test_create_token_no_pwd',
]

class AuthObjectTestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)
        
    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    #
    # keyauth token
    #
    def test_create_token(self):
        data = {u'user':self.users[u'admin'][u'user'], 
                u'password':self.users[u'admin'][u'pwd'],
                u'login-ip':self.users[u'admin'][u'ip'],
                u'porva':None}
        self.call(u'auth', u'/v1.0/keyauth/token', u'post', data=data)
    
    @assert_exception(BadRequestException)
    def test_create_token_wrong_user_syntax(self):
        data = {u'user':u'pippo', 
                u'password':u'mypass'}
        self.call(u'auth', u'/v1.0/keyauth/token', u'post', data=data)
        
    @assert_exception(NotFoundException)
    def test_create_token_wrong_user(self):
        data = {u'user':u'pippo@local', 
                u'password':u'mypass'}
        self.call(u'auth', u'/v1.0/keyauth/token', u'post', data=data)
        
    @assert_exception(UnauthorizedException)
    def test_create_token_wrong_pwd(self):
        data = {u'user':self.users[u'admin'][u'user'], 
                u'password':u'mypass'}
        self.call(u'auth', u'/v1.0/keyauth/token', u'post', data=data) 

    @assert_exception(BadRequestException)
    def test_create_token_no_user(self):
        data = {u'password':self.users[u'admin'][u'pwd']}
        self.call(u'auth', u'/v1.0/keyauth/token', u'post', data=data)
    
    @assert_exception(BadRequestException)
    def test_create_token_no_pwd(self):
        data = {u'user':self.users[u'admin'][u'user']}
        self.call(u'auth', u'/v1.0/keyauth/token', u'post', data=data)
     
if __name__ == u'__main__':
    runtest(AuthObjectTestCase, tests)      