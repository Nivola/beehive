#!/usr/bin/env python

# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

from os import environ
from sys import prefix, version_info
from setuptools import setup
from setuptools.command.install import install as _install


class install(_install):
    def pre_install_script(self):
        pass

    def post_install_script(self):
        pass

    def run(self):
        self.pre_install_script()

        _install.run(self)

        self.post_install_script()


def install_requires(requires):
    if version_info.major == 3:
        requires.append("ipaddress==1.0.23")
    else:
        requires.append("py2-ipaddress==3.4.1")
    return requires


if __name__ == '__main__':
    prefix = environ.get('VIRTUAL_ENV')
    f = open('/tmp/log', 'w')
    f.write(prefix)
    f.write('\n')
    f.write(prefix)
    f.close()

    setup(
        name='beehive',
        version='1.5',
        description='Nivola core',
        long_description='Nivola main server package',
        author='CSI Piemonte',
        author_email='nivola.engineering@csi.it',
        license='GPL v3',
        url='',
        scripts=[],
        packages=[
            'beehive.common',
            'beehive.common.controller',
            'beehive.common.model',
            'beehive.common.task',
            'beehive.module',
            'beehive.module.auth',
            'beehive.module.auth.views',
            'beehive.module.basic',
            'beehive.module.catalog',
            'beehive.module.config',
            'beehive.module.event',
            'beehive.module.scheduler',
            'beehive.server',
            'beehive.tests',
            'beehive.tests.common',
            'beehive.tests.glb',
            'beehive.tests.module',
            'beehive.tests.module.auth',
            'beehive.tests.module.basic',
            'beehive.tests.module.catalog',
            'beehive.tests.module.config',
            'beehive.tests.module.event',
            'beehive.tests.module.scheduler',
            'beehive.tests.regression',
        ],
        namespace_packages=[],
        py_modules=[
            'beehive.__init__'
        ],
        classifiers=[
            'Development Status :: 1.5',
            'Programming Language :: Python'
        ],
        entry_points={},
        data_files=[
            ('share/config', ['config/auth.json',
                                      'config/event.json',
                                      'config/auth.ini',
                                      'config/event.ini']),
            ('bin', ['beehive/server/api.py',
                               'beehive/server/task.py',
                               'beehive/server/scheduler.py',
                               'beehive/server/catalog.py',
                               'beehive/server/event.py',
                               'beehive/server/console.py']),
        ],
        package_data={},
        install_requires=install_requires([
            "SQLAlchemy==1.3.7",
            "Flask==1.1.1",
            "Flask-Babel==0.12.2",
            "Flask-Login==0.4.1",
            "Flask-SQLAlchemy==2.4.0",
            "Flask-WTF==0.14.2",
            "Flask-Session==0.3.1",
            "anyjson==0.3.3",
            "pika==1.1.0",
            "Paramiko==2.6.0",
            "blessings==1.7.0",
            "pygments==2.4.2",
            "psutil==5.6.3",
            "PrettyTable==0.7.2",
            "redis==3.0.1",
            "passlib==1.7.1",
            "pymysql==0.9.3",
            "httplib2==0.13.1",
            "pymongo==3.9.0",
            "ujson==1.35",
            "hiredis==1.0.0",
            "gevent==1.4.0",
            "docutils==0.15.2",
            "python-ldap==3.2.0",
            "pyzmq==18.1.0",
            "os-client-config==1.32.0",
            "dicttoxml==1.7.4",
            #"pyvmomi==6.7.1.2018.12",
            "oslo.utils==3.41.0",
            "easywebdav==1.2.0",
            "networkx==2.2",
            "cryptography==2.7",
            "celery==4.2.2",
            "kombu==4.3.0",
            "urllib3==1.25.3",
            "pyopenssl==19.0.0",
            "pycrypto==2.6.1",
            "xmltodict==0.12.0",
            "PyYAML==5.1.2",
            "proxmoxer==1.0.3",
            "geventhttpclient==1.3.1",
            "tabulate==0.8.3",
            "ansible==2.8.4",
            "oauthlib==3.1.0",
            "requests_oauthlib==1.2.0",
            "pyjwt==1.7.1",
            "bcrypt==3.1.7",
            "flasgger==0.9.0",
            "marshmallow==2.19.5",
            "apispec==0.38.0",
            "flex==6.14.0",
            "redis-py-cluster==2.0.0",
            "requests==2.22.0",
            "setuptools==41.2.0",
            "librabbitmq==2.0.0",
            "dnspython==1.16.0",
            "python-dateutil==2.8.0",
            "billiard==3.6.0",
            "elasticsearch==7.0.4",
            "uwsgi==2.0.18",
            "click==7.0"
        ]),
        dependency_links=[],
        zip_safe=True,
        cmdclass={'install': install},
        keywords='',
        python_requires='',
        obsoletes=[]
    )
