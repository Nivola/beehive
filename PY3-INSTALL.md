# Install in a python 3.5> environment

## Installing

### Install requirements
First of all you have to install some package:

```
$ sudo apt-get install gcc
$ sudo apt-get install -y python-dev libldap2-dev libsasl2-dev libssl-dev
```

### Create python virtualenv
At this point create a virtualenv

```
$ python3 -m venv /tmp/beehive-py3-test-env
$ source /tmp/beehive-py3-test-env/bin/activate
$ pip3 install wheel
```

### Install python packages

public packages:

```
$ pip3 install -U git+https://github.com/Nivola/beecell.git
$ pip3 install -U git+https://github.com/Nivola/beehive.git
```

internal packages:

```
$ pip3 install -U git+https://gitlab.csi.it/nivola/cmp3/beecell.git@devel
$ pip3 install -U git+https://gitlab.csi.it/nivola/cmp2/beehive.git@devel
```
