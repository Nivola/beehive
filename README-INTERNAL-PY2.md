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
$ python /tmp/beehive-py2-test-env/bin/console.py init auth
```

#### Run auth server

```
$ python /tmp/beehive-py2-test-env/bin/console.py start auth
```

##### Inspect server logs

```
$ tail -f /tmp/uwsgi.auth.log
$ tail -f auth-01.log
```

##### Make some simple test

```
$ curl http://localhost:8080/v1.0/server/ping
$ curl http://localhost:8080/v1.0/server
```

##### Make some interesting test

Create an authentication token:

```
$ python /tmp/beehive-py2-test-env/bin/console.py create-token
token: ...
seckey: ...
```

Make simple api requests using authentication token:

```
$ python /tmp/beehive-py2-test-env/bin/console.py get-tokens <token> <seckey>
$ python /tmp/beehive-py2-test-env/bin/console.py get-users <token> <seckey>
```

#### Stop auth server

```
$ python /tmp/beehive-py2-test-env/bin/console.py stop auth
```

#### Remove servers database configuration

```
$ python /tmp/beehive-py2-test-env/bin/console.py drop
```

## Getting Started
Instructions useful to deploy software on a simple environment (local machine or simple server configuration infrastructure).

## Running the tests
Results of vulnerability assessment and/or penetration test.

- Activate virtual env

```
$ source /tmp/beehive-py2-test-env/bin/activate
```

- Open tests directory __/tmp/beehive-py2-test-env/lib/python2.7/site-packages/beehive/tests__
- Copy file beehive.yml from /tmp/beehive-py2-test-env/share/test in your home directory. Open the file and set 
  correctly all the <BLANK> variables.
- Run some tests:

```
$ python module/basic/view.py conf=/tmp/beehive-py2-test-env/share/test/beehive.yml
```

## Versioning
We use Semantic Versioning for versioning. (http://semver.org)

## Authors and Contributors
See the list of contributors who participated in this project in the file AUTHORS.md contained in each specific project.

## Copyright
CSI Piemonte - 2018-2019

## License
See the LICENSE.txt file for details
