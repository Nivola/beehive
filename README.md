# beehive
__beehive__ is a project that contains the core of the nivola cmp platform. With beehive you can start the authorization
module, the api endpoint catalog, the base scheduler module and the event module.
All code is written using python and support versions 3.7.x>. Python was deployed using basic linux process
and uwsgi as application server.

Beehive is deployed using subsystem. A subsystem is composed of a database (mysql) schema, some redis (or rabbimq) queue,
a redis database where store keys, some python process.

Subsytem runtime is composed of:

- a uwsgi api server
- some python processes with celery worker
- a python process with celery beat
- some python processes with custom kombu queue consumer

Miminal subsystem to deploy are:

- auth subsytem: the first to configure and deploy. It is composed by base module, auth module, catalog module and
  scheduler module.
- event subsystem: useful to store system events. It is composed by base module, event module, and scheduler module.

## Installing

### Install requirements
First of all you have to install some package:

```
$ sudo apt-get install gcc
$ sudo apt-get install -y python-dev libldap2-dev libsasl2-dev libssl-dev
```

At this point create a virtualenv

```
$ python3 -m venv /tmp/py3-test-env
$ source /tmp/py3-test-env/bin/activate
$ pip3 install wheel
```

### Install python packages

public packages:

```
$ pip3 install -U git+https://github.com/Nivola/beecell.git
$ pip3 install -U git+https://github.com/Nivola/beehive.git
```


## Running the tests
Before you begin with tests, you have to deploy CMP: see README in [nivola](https://github.com/Nivola/nivola)

Activate virtual env:

```
$ source /tmp/py3-test-env/bin/activate
```

Open tests directory __/tmp/py3-test-env/lib/python[3.x]/site-packages/beehive/tests__

Copy file beehive.yml from /tmp/py3-test-env/share/test in your home directory.
Open the file and set correctly the <BLANK> variables.
In particular:
- the endpoints:
  auth: https://<HOST_NGINX>:443/mylab
  event: https://<HOST_NGINX>:443/mylab
  ssh: https://<HOST_NGINX>:443/mylab
- reference to redis that runs in minikube: <MINIKUBE_IP>, <REDIS_SERVICE_PORT> (can you obtain information lanching: kubectl -n beehive-mylab get services | grep redis)



Copy file beehive.fernet from /tmp/py3-test-env/share/test in your home directory.

Run tests:

Test log can be seen in the home directory.
Files:
- __test.run__
- __test.log__

```
Optionally specify the path to the beehive.yml file with param
  conf=/tmp/py3-test-env/share/test/beehive.yml

$ python module/basic/view.py
$ python module/auth/view_keyauth.py
$ python module/auth/view.py  user=admin
$ python module/catalog/view.py  user=admin
$ python module/scheduler_v2/view.py  user=admin
$ python module/event/view.py  user=admin
$ python module/event/producer.py  user=admin
```


## Versioning
We use Semantic Versioning for versioning. (https://semver.org)

## Authors and Contributors
See the list of contributors who participated in this project in the file AUTHORS.md contained in each specific project.

## Copyright
CSI Piemonte - 2018-2024

Regione Piemonte - 2020-2022

## License
See EUPL v1_2 EN-LICENSE.txt or EUPL v1_2 IT-LICENSE.txt file for details

## Community site (Optional)
At https://www.nivolapiemonte.it/ could find all the informations about the project.
