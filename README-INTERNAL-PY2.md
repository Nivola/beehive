# beehive
__beehive__ is a project that contains tha core of the nivola cmp platform.

## Configurations (Optional)
Software parameters and their meaning.

## Prerequisites
Fundamental requirements is python 2.7.x or python 3.5>.

Required middleware:

- mysql 5.7.x o mariadb 10.x
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

### Init auth module

```
$ python /tmp/beehive-py2-test-env/bin/console.py init auth
```

### Run auth server

```
$ python /tmp/beehive-py2-test-env/bin/console.py start auth
```

#### Inspect auth server logs

Open directory /tmp

- auth-01.log
- auth-01.uwsgi.log
- auth-01.catalog.consumer.log  
- auth-01.catalog.log  
- auth-01.scheduler.log  
- auth-01.task.log
- auth-01.worker1.log

```
$ tail -f /tmp/auth-01.log
```

### Test auth server

#### Make some simple test

```
$ curl http://localhost:8080/v1.0/server/ping
$ curl http://localhost:8080/v1.0/server
```

#### Make some interesting test

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

### Init event module

```
$ python /tmp/beehive-py2-test-env/bin/console.py init event
```

### Run event server

```
$ python /tmp/beehive-py2-test-env/bin/console.py start event
```

#### Inspect event server logs

Open directory /tmp

- event-01.log
- event-01.uwsgi.log
- event-01.event.consumer.log  
- event-01.event.log  
- event-01.scheduler.log  
- event-01.task.log
- event-01.worker1.log

```
$ tail -f /tmp/event-01.log
```

### Test event server

#### Make some simple test

```
$ curl http://localhost:8081/v1.0/server/ping
$ curl http://localhost:8081/v1.0/server
```

### Inspect api and access logs

Open directory /tmp

- apis.log
- accesses.log

## Running the tests
Results of vulnerability assessment and/or penetration test.

Activate virtual env:

```
$ source /tmp/beehive-py2-test-env/bin/activate
```

Open tests directory __/tmp/beehive-py2-test-env/lib/python2.7/site-packages/beehive/tests__

Copy file beehive.yml from /tmp/beehive-py2-test-env/share/test in your home directory. Open the file and set 
  correctly all the <BLANK> variables.

Run tests:

Test log can be seen in the home directory. 
Files: 
- __test.run__ 
- __test.log__

```
$ python module/basic/view.py conf=/tmp/beehive-py2-test-env/share/test/beehive.yml
$ python module/auth/view_keyauth.py conf=/tmp/beehive-py2-test-env/share/test/beehive.yml
$ python module/auth/view.py conf=/tmp/beehive-py2-test-env/share/test/beehive.yml user=admin
$ python module/catalog/view.py conf=/tmp/beehive-py2-test-env/share/test/beehive.yml user=admin
$ python module/scheduler/view.py conf=/tmp/beehive-py2-test-env/share/test/beehive.yml user=admin
$ python module/event/view.py conf=/tmp/beehive-py2-test-env/share/test/beehive.yml user=admin
```


## Administration

### Stop auth server

```
$ python /tmp/beehive-py2-test-env/bin/console.py stop auth-01
```

### Stop event server

```
$ python /tmp/beehive-py2-test-env/bin/console.py stop event-01
```

### Remove current installation

```
$ python /tmp/beehive-py2-test-env/bin/console.py drop
```


## Versioning
We use Semantic Versioning for versioning. (http://semver.org)

## Authors and Contributors
See the list of contributors who participated in this project in the file AUTHORS.md contained in each specific project.

## Copyright
CSI Piemonte - 2018-2019

## License
See the LICENSE.txt file for details
