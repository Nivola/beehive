beehive_
==============

Latest Version: 0.1.0

beehive is the core api compoennt used by gibbonportal to communicate with cloud
cloud orchestrator and virtualization system.

Features included:

* Async http execution based on uwsgi/gevent
  * Fast event loop based on libev_.
  * Lightweight execution units based on greenlet_.
* Expose standard cloudstack api
* Expose extended cloudstack api
* Expose coarse grained cloud api used by the gibbonportal_

gevent_ is `inspired by eventlet`_ but features more consistent API, simpler implementation and better performance. Read why others `use gevent`_ and check out the list of the `open source projects based on gevent`_.

beehive_ is written and maintained by `Sergio Tonani`_ and `Pasquale Lepera`_ and is licensed under MIT license.


get beehive
------------------

Install Python 2.7.* and the following package:

Download the latest release from `Python Package Index`_ or clone `the repository`_.

Read the documentation online at http://.....

Post feedback and issues on the `bug tracker`_, `mailing list`_, blog_ and `twitter (@gevent)`_.


installing from github
----------------------

To install the latest development version:

  pip install cython git+git://github.com/......


running tests
-------------

  python setup.py build

  cd greentest

  PYTHONPATH=.. python testrunner.py --expected ../known_failures.txt

-- beehive_: http://
.. _gevent: http://www.gevent.org
.. _greenlet: http://pypi.python.org/pypi/greenlet
.. _libev: http://libev.schmorp.de/
.. _c-ares: http://c-ares.haxx.se/
.. _use gevent: http://groups.google.com/group/gevent/browse_thread/thread/4de9703e5dca8271
.. _open source projects based on gevent: https://github.com/surfly/gevent/wiki/Projects
.. _Sergio Tonani: http://...
.. _Pasquale Lepera: http://...
.. _Python Package Index: http://pypi.python.org/pypi/...
.. _the repository: https://github.com/...
.. _bug tracker: $$$$$$https://github.com/surfly/gevent/wiki/Projects
.. _mailing list: $$$$$$$http://groups.google.com/group/gevent
.. _blog: $$$$$$http://blog.gevent.org
.. _twitter $$$$$$ (@gevent): http://twitter.com/gevent