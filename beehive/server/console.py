#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import click
import os
from sys import prefix

import requests

from beehive.common.helper import BeehiveHelper

#CREATE SCHEMA `auth` DEFAULT CHARACTER SET latin1;
# CREATE USER 'newuser'@'%' IDENTIFIED BY 'user_password';
#GRANT ALL PRIVILEGES ON database_name.* TO 'database_user'@'%';

MYSQL_INIT = [
    {'schema': 'auth', 'user': 'auth', 'pwd': 'auth'},
    {'schema': 'event', 'user': 'event', 'pwd': 'event'},
]
BASE_MYSQL_CMD = 'mysql -u root -e'
MYSQL_PWD = '-p %s'
MYSQL_CREATE_SCHEMA = "CREATE SCHEMA IF NOT EXISTS `{schema}` DEFAULT CHARACTER SET latin1;"
MYSQL_DROP_SCHEMA = "DROP SCHEMA IF EXISTS `{schema}`;"
MYSQL_CREATE_USER = 'CREATE USER IF NOT EXISTS `{user}`@`{host}` IDENTIFIED BY "{pwd}";'
MYSQL_DROP_USER = 'DROP USER IF EXISTS `{user}`@`{host}`;'
MYSQL_AUTH_USER = 'GRANT ALL ON {schema}.* TO `{user}`@`{host}`; FLUSH PRIVILEGES;'


def run_cmd(cmd, trace=False):
    # click.echo(cmd)
    out = os.popen(cmd).read()
    if trace is True:
        print(out)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('module')
@click.option('--pwd', default=None, help='mysql root password')
@click.option('--client', default='localhost', help='mysql root host client')
@click.option('--path', default=None, help='configuration files path')
def init(module, pwd, path, client):
    click.echo('Initialize the database')
    mysql_cmd = BASE_MYSQL_CMD
    if pwd is not None:
        mysql_cmd += MYSQL_PWD % pwd
    mysql_cmd += " '{sql}'"

    for item in MYSQL_INIT:
        schema = item.get('schema')
        if schema != module:
            continue
        user = item.get('user')
        pwd = item.get('pwd')
        click.echo('create schema {schema}'.format(schema=schema))
        run_cmd(mysql_cmd.format(sql=MYSQL_CREATE_SCHEMA.format(schema=schema)))
        click.echo('create user {user}@{client}'.format(user=user, client=client))
        run_cmd(mysql_cmd.format(sql=MYSQL_CREATE_USER.format(user=user, pwd=pwd, host=client)))
        click.echo('set user {user}@{client} authorization'.format(user=user, client=client))
        run_cmd(mysql_cmd.format(sql=MYSQL_AUTH_USER.format(schema=schema, user=user, host=client)))

    for item in MYSQL_INIT:
        schema = item.get('schema')
        if schema != module:
            continue
        helper = BeehiveHelper()
        if path is None:
            path = prefix + '/share/config'
        config = path + '/{schema}.json'.format(schema=schema)
        res = helper.create_subsystem(config)
        # click.echo(res)


@cli.command()
@click.option('--pwd', default=None, help='mysql root password')
@click.option('--client', default='localhost', help='mysql root host client')
def drop(pwd, client):
    click.echo('Drop the database')

    mysql_cmd = BASE_MYSQL_CMD
    if pwd is not None:
        mysql_cmd += MYSQL_PWD % pwd
    mysql_cmd += " '{sql}'"

    for item in MYSQL_INIT:
        schema = item.get('schema')
        user = item.get('user')
        click.echo('drop user {user}@{client}'.format(user=user, client=client))
        run_cmd(mysql_cmd.format(sql=MYSQL_DROP_USER.format(user=user, host=client)))
        click.echo('drop schema {schema}'.format(schema=schema))
        run_cmd(mysql_cmd.format(sql=MYSQL_DROP_SCHEMA.format(schema=schema)))


@cli.command()
@click.argument('system')
def start(system):
    click.echo('start server')
    run_cmd('uwsgi -i ../share/config/%s.ini' % system)


@cli.command()
@click.argument('system')
def stop(system):
    click.echo('stop server')
    run_cmd('uwsgi --stop /tmp/uwsgi.%s.pid' % system)


@cli.command()
@click.argument('system')
def restart(system):
    click.echo('stop server')
    run_cmd('uwsgi --stop /tmp/uwsgi.%s.pid' % system)
    click.echo('start server')
    run_cmd('uwsgi -i ../share/config/%s.ini' % system)


@cli.command()
def create_token(self):
    data = {
        'user': 'admin@local',
        'password': 'admin',
        'login-ip': 'localhost'
    }
    res = requests.post('http://localhost:8080/v1.0/nas/keyauth/token', data=data)
    print(res.json())


if __name__ == '__main__':
    cli()
