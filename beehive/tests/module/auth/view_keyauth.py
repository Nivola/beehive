# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from beehive.common.test import runtest, BeehiveTestCase, assert_exception
from beecell.remote import BadRequestException, NotFoundException, UnauthorizedException

tests = [
    "test_create_token",
    "test_create_token_wrong_user_syntax",
    "test_create_token_wrong_user",
    "test_create_token_wrong_pwd",
    "test_create_token_no_user",
    "test_create_token_no_pwd",
]


class AuthObjectTestCase(BeehiveTestCase):
    def setUp(self):
        BeehiveTestCase.setUp(self)
        self.module = "auth"
        self.module_prefix = "nas"
        self.endpoint_service = "auth"

    def tearDown(self):
        BeehiveTestCase.tearDown(self)

    def test_create_token(self):
        data = {
            "user": self.users["test1"]["user"],
            "password": self.users["test1"]["pwd"],
            "login-ip": self.users["test1"]["ip"],
        }
        self.post("/v1.0/nas/keyauth/token", data=data)

    @assert_exception(BadRequestException)
    def test_create_token_wrong_user_syntax(self):
        data = {"user": "test1", "password": "mypass"}
        self.post("/v1.0/nas/keyauth/token", data=data)

    @assert_exception(NotFoundException)
    def test_create_token_wrong_user(self):
        data = {"user": "prova@local", "password": "mypass"}
        self.post("/v1.0/nas/keyauth/token", data=data)

    @assert_exception(UnauthorizedException)
    def test_create_token_wrong_pwd(self):
        data = {"user": self.users["test1"]["user"], "password": "mypass"}
        self.post("/v1.0/nas/keyauth/token", data=data)

    @assert_exception(BadRequestException)
    def test_create_token_no_user(self):
        data = {"password": self.users["test1"]["pwd"]}
        self.post("/v1.0/nas/keyauth/token", data=data)

    @assert_exception(BadRequestException)
    def test_create_token_no_pwd(self):
        data = {"user": self.users["test1"]["user"]}
        self.post("/v1.0/nas/keyauth/token", data=data)


def run(args):
    runtest(AuthObjectTestCase, tests, args)


if __name__ == "__main__":
    run({})
