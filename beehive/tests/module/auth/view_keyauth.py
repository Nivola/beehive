'''
Created on Aug 9, 2017

@author: darkbk
'''
from beehive.common.test import runtest, BeehiveTestCase, assert_exception
from beecell.remote import BadRequestException, NotFoundException,\
    UnauthorizedException

tests = [
    'test_create_token',
    # 'test_create_token_wrong_user_syntax',
    # 'test_create_token_wrong_user',
    # 'test_create_token_wrong_pwd',
    # 'test_create_token_no_user',
    # 'test_create_token_no_pwd',
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
        data = {'user':self.users['admin']['user'], 
                'password':self.users['admin']['pwd'],
                'login-ip':self.users['admin']['ip'],
                'porva':None}
        self.call('auth', '/v1.0/nas/keyauth/token', 'post', data=data)
    
    @assert_exception(BadRequestException)
    def test_create_token_wrong_user_syntax(self):
        data = {'user':'pippo', 
                'password':'mypass'}
        self.call('auth', '/v1.0/nas/keyauth/token', 'post', data=data)
        
    @assert_exception(NotFoundException)
    def test_create_token_wrong_user(self):
        data = {'user':'pippo@local', 
                'password':'mypass'}
        self.call('auth', '/v1.0/nas/keyauth/token', 'post', data=data)
        
    @assert_exception(UnauthorizedException)
    def test_create_token_wrong_pwd(self):
        data = {'user':self.users['admin']['user'], 
                'password':'mypass'}
        self.call('auth', '/v1.0/nas/keyauth/token', 'post', data=data) 

    @assert_exception(BadRequestException)
    def test_create_token_no_user(self):
        data = {'password':self.users['admin']['pwd']}
        self.call('auth', '/v1.0/nas/keyauth/token', 'post', data=data)
    
    @assert_exception(BadRequestException)
    def test_create_token_no_pwd(self):
        data = {'user':self.users['admin']['user']}
        self.call('auth', '/v1.0/nas/keyauth/token', 'post', data=data)


if __name__ == '__main__':
    runtest(AuthObjectTestCase, tests)
