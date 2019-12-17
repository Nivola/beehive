# beehive
__beehive__ is a project that contains tha core of the nivola cmp platform.

## Installing

[Install in a python 2.7.x environment](PY2-INSTALL.md)

[Install in a python 3.5.x> environment](PY3-INSTALL.md)

### Init auth module

```
$ python /tmp/beehive-py[2|3]-test-env/bin/console.py init auth
```

### Run auth server

```
$ python /tmp/beehive-py[2|3]-test-env/bin/console.py start auth
```

#### Inspect auth server logs

Open directory /tmp. If server started correctly you can find these files:

- auth-01.api.log
- auth-01.api.out
- auth-01.catalog.log  
- auth-01.catalog.out  
- auth-01.scheduler.log
- auth-01.scheduler.out
- auth-01.worker.log
- auth-01.worker.out

Inspect main api server log file:

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
$ python /tmp/beehive-py[2|3]-test-env/bin/console.py create-token
token: ...
seckey: ...
```

Make simple api requests using authentication token:

```
$ python /tmp/beehive-py[2|3]-test-env/bin/console.py get-tokens <token> <seckey>
$ python /tmp/beehive-py[2|3]-test-env/bin/console.py get-users <token> <seckey>
```

### Init event module

```
$ python /tmp/beehive-py[2|3]-test-env/bin/console.py init event
```

### Run event server

```
$ python /tmp/beehive-py[2|3]-test-env/bin/console.py start event
```

#### Inspect event server logs

Open directory /tmp. If server started correctly you can find these files:

- event-01.api.log
- event-01.api.out
- event-01.event.consumer.log  
- event-01.event.log  
- event-01.scheduler.log
- event-01.scheduler.out
- event-01.worker.log
- event-01.worker.out

Inspect main api server log file:

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

Open directory /tmp.

- apis.log
- accesses.log

## Running the tests
Activate virtual env:

```
$ source /tmp/beehive-py[2|3]-test-env/bin/activate
```

Open tests directory __/tmp/beehive-py[2|3]-test-env/lib/python[2.7|3.x]/site-packages/beehive/tests__

Copy file beehive.yml from /tmp/beehive-py[2|3]-test-env/share/test in your home directory. Open the file and set 
  correctly all the <BLANK> variables.

Run tests:

Test log can be seen in the home directory. 
Files: 
- __test.run__ 
- __test.log__

```
$ python module/basic/view.py conf=/tmp/beehive-py[2|3]-test-env/share/test/beehive.yml
$ python module/auth/view_keyauth.py conf=/tmp/beehive-py[2|3]-test-env/share/test/beehive.yml
$ python module/auth/view.py conf=/tmp/beehive-py[2|3]-test-env/share/test/beehive.yml user=admin
$ python module/auth/tasks.py conf=/tmp/beehive-py[2|3]-test-env-01/share/test/beehive.yml user=admin
$ python module/catalog/view.py conf=/tmp/beehive-py[2|3]-test-env/share/test/beehive.yml user=admin
$ python module/catalog/tasks.py conf=/tmp/beehive-py[2|3]-test-env-01/share/test/beehive.yml user=admin
$ python module/scheduleruler_v2/tasks.py conf=/tmp/beehive-py[2|3]-test-env/share/test/beehive.yml user=admin
$ python module/scheduleruler_v2/view.py conf=/tmp/beehive-py[2|3]-test-env/share/test/beehive.yml user=admin
$ python module/event/view.py conf=/tmp/beehive-py[2|3]-test-env/share/test/beehive.yml user=admin
$ python module/event/producer.py conf=/tmp/beehive-py[2|3]-test-env/share/test/beehive.yml user=admin
```

## Administration

### Stop auth server

```
$ python /tmp/beehive-py[2|3]-test-env/bin/console.py stop auth-01
```

### Stop event server

```
$ python /tmp/beehive-py[2|3]-test-env/bin/console.py stop event-01
```

### Remove current installation

```
$ python /tmp/beehive-py[2|3]-test-env/bin/console.py drop
```

## Versioning
We use Semantic Versioning for versioning. (http://semver.org)

## Authors and Contributors
See the list of contributors who participated in this project in the file AUTHORS.md contained in each specific project.

## Copyright
CSI Piemonte - 2018-2019

## License
See the LICENSE.txt file for details
