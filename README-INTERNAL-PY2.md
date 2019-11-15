# beehive
__beehive__ is a project that contains tha core of the nivola cmp platform.

## Configurations (Optional)
Software parameters and their meaning.

## Prerequisites
Fundamental requirements is python 3.5>.

Required middleware:

- mysql 5.7.x
- redis 5.x

First of all you have to install some package:

```
$ sudo apt-get install gcc
$ sudo apt-get install -y python-dev libldap2-dev libsasl2-dev libssl-dev
```

At this point create a virtual env

```
$ virtualenv /tmp/beehive-py2-test-env
$ source /tmp/beehive-py2-test-env/bin/activate
```

## Installing

```
$ pip install -U git+https://gitlab.csi.it/nivola/cmp3/beecell.git@devel
$ pip install -U git+https://gitlab.csi.it/nivola/cmp2/beehive.git@devel
```

### Post configuration

#### Init auth module

```
$ python console.py init auth --path=/tmp/beehive-py2-test-env/share/config
```

#### Run auth server

```
$ uwsgi -i share/config/auth.ini
```

#### Init event module

```
$ python console.py init event --path=/tmp/beehive-test-env/share/config
```

### Run servers

#### Run auth server

```
uwsgi -i share/config/event.ini
```

### Reload server
# using kill to send the signal
kill -HUP `cat /tmp/project-master.pid`
# or the convenience option --reload
uwsgi --reload /tmp/project-master.pid

### Stop server
kill -INT `cat /tmp/project-master.pid`
# or for convenience...
uwsgi --stop /tmp/project-master.pid

## Getting Started
Instructions useful to deploy software on a simple environment (local machine or simple server configuration infrastructure).

## Running the tests
Results of vulnerability assessment and/or penetration test. If known explain how to run the automated tests for this system

- Activate virtual env

```
$ source venv/bin/activate
```

- Open tests directory __beecell/tests__
- Copy file beecell.yml in your home directory. Open the file and set correctly all the <BLANK> variables.
- Run some tests:

```
$ python sendmail.py
$ python cement_cmd.py 
$ python paramiko_shell.py 
$ python networkx_layout.py
$ python db/manager_mysql.py 
$ python db/manager_redis.py
$ python db/manager_redis_cluster.py 
$ python auth/perm.py 
$ python auth/ldap_auth.py 
$ python auth/database_auth.py 
```

## Versioning
We use Semantic Versioning for versioning. (http://semver.org)

## Authors and Contributors
See the list of contributors who participated in this project in the file AUTHORS.md contained in each specific project.

## Copyright
CSI Piemonte - 2018-2019

## License
See the LICENSE.txt file for details
