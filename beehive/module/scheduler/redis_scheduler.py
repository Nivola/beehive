'''
Created on Nov 13, 2015

@author: darkbk
'''
import ujson as json
from beecell.db.manager import RedisManager
from celery.beat import Scheduler
from datetime import timedelta
import traceback
import datetime
import shelve
from celery.schedules import maybe_schedule, crontab, schedule as interval
from celery.five import items
from kombu.utils import cached_property, reprcall
from celery.beat import PersistentScheduler
import redis_collections
#import pickle

class RedisScheduleEntry(object):
    """An entry in the scheduler.

    :keyword name: see :attr:`name`.
    :keyword schedule: see :attr:`schedule`.
    :keyword args: see :attr:`args`.
    :keyword kwargs: see :attr:`kwargs`.
    :keyword options: see :attr:`options`.
    :keyword last_run_at: see :attr:`last_run_at`.
    :keyword total_run_count: see :attr:`total_run_count`.
    :keyword relative: Is the time relative to when the server starts?

    """

    #: The task name
    name = None

    #: The schedule (run_every/crontab)
    schedule = None

    #: Positional arguments to apply.
    args = None

    #: Keyword arguments to apply.
    kwargs = None

    #: Task execution options.
    options = None

    #: The time and date of when this task was last scheduled.
    last_run_at = None

    #: Total number of times this task has been scheduled.
    total_run_count = 0

    def __init__(self, name=None, task=None, last_run_at=None,
                 total_run_count=None, schedule=None, args=(), kwargs={},
                 options={}, relative=False, app=None):
        self.app = app
        self.name = name
        self.task = task
        self.args = args
        self.kwargs = kwargs
        self.options = options
        self.schedule = maybe_schedule(schedule, relative, app=self.app)
        self.last_run_at = last_run_at or self._default_now()
        self.total_run_count = total_run_count or 0

    def _default_now(self):
        return self.schedule.now() if self.schedule else self.app.now()

    def _next_instance(self, last_run_at=None):
        """Return a new instance of the same class, but with
        its date and count fields updated."""
        return self.__class__(**dict(
            self,
            last_run_at=last_run_at or self._default_now(),
            total_run_count=self.total_run_count + 1,
        ))
    __next__ = next = _next_instance  # for 2to3

    def __reduce__(self):
        return self.__class__, (
            self.name, self.task, self.last_run_at, self.total_run_count,
            self.schedule, self.args, self.kwargs, self.options,
        )

    def update(self, other):
        """Update values from another entry.

        Does only update "editable" fields (task, schedule, args, kwargs,
        options).

        """
        self.__dict__.update({'task': other.task, 'schedule': other.schedule,
                              'args': other.args, 'kwargs': other.kwargs,
                              'options': other.options})

    def is_due(self):
        """See :meth:`~celery.schedule.schedule.is_due`."""
        return self.schedule.is_due(self.last_run_at)

    def __iter__(self):
        return iter(items(vars(self)))

    def __repr__(self):
        return '<Entry: {0.name} {call} {0.schedule}'.format(
            self,
            call=reprcall(self.task, self.args or (), self.kwargs or {}),
        )
        
    def info(self):
        """ """
        res = {'name': self.name,
               'task':self.task,
               'schedule':str(self.schedule),
               'args':self.args,
               'kwargs':self.kwargs,
               'options':self.options,
               'last_run_at':self.last_run_at,
               'total_run_count':self.total_run_count}
        return res

class PersistentScheduler2(PersistentScheduler):

    def get_schedule(self):
        print self._store['entries']
        return self._store['entries']

    def set_schedule(self, schedule):
        print schedule
        self._store['entries'] = schedule
    schedule = property(get_schedule, set_schedule)

    def sync(self):
        if self._store is not None:
            self._store.sync()

    def close(self):
        self.sync()
        self._store.close()

    @property
    def info(self):
        return '    . db -> {self.schedule_filename}'.format(self=self)

class RedisScheduler(Scheduler):
    Entry = RedisScheduleEntry

    def __init__(self, app, schedule=None, max_interval=None,
                 Publisher=None, lazy=False, sync_every_tasks=None, **kwargs):
        #self.schedule_filename = kwargs.get('schedule_filename')
        redis_uri = app.conf.CELERY_SCHEDULE_BACKEND
        # set redis manager
        self.manager = RedisManager(redis_uri)
        #keys = self.manager.inspect(pattern='*', debug=False)
        
        self._prefix = app.conf.CELERY_REDIS_SCHEDULER_KEY_PREFIX
        
        self._schedule = redis_collections.Dict(key=self._prefix, redis=self.manager.conn)
        self.logger.info(self._schedule)
        Scheduler.__init__(self, app, schedule=schedule, 
                           max_interval=max_interval, Publisher=Publisher, 
                           lazy=lazy, sync_every_tasks=sync_every_tasks, **kwargs)
    
    def update_from_dict(self, dict_):
        self.logger.info(dict_)
        for name, entry in items(dict_):
            self.logger.info(name)
            self.logger.info(self._maybe_entry(name, entry))
    
    def get_schedule(self):
        #print 'GET', self._schedule
        return self._schedule

    def set_schedule(self, schedule):
        #print 'SET', schedule
        self.data = schedule
        
    schedule = property(get_schedule, set_schedule)
    
    def setup_schedule(self):
        #self.install_default_entries(self.schedule)
        self.update_from_dict(self.app.conf.CELERYBEAT_SCHEDULE)
    
    '''
    def update_from_dict(self, dict_):
        self.schedule['pippo'] = 'pppp'
        self.schedule.update(dict(
            (name, self._maybe_entry(name, entry))
            for name, entry in items(dict_)))
    
    def update_from_dict2(self, dict_):
        s = {}
        for name, entry in dict_.items():
            s[name] = self.from_entry(name, **entry)
            print s
        #self.schedule.update(s)    
        self.manager.conn.set(self._prefix+name, json.dumps(s))
    
    def add_sched(self, name, task, last_run_at=None, total_run_count=0, 
                  schedule=None, args=None, kwargs=None, options=None):
        value = {'task':task,
                 'last_run_at':last_run_at,
                 'total_run_count':total_run_count,
                 'schedule':schedule,
                 'args':args,
                 'kwargs':kwargs,
                 'options':options}
        self.manager.conn.set(self._prefix+name, json.dumps(value))
    '''

    '''
    def requires_update(self):
        """check whether we should pull an updated schedule
        from the backend database"""
        if not self._last_updated:
            return True
        return self._last_updated + self.UPDATE_INTERVAL < datetime.datetime.now()

    @property
    def schedule(self):
        if self.requires_update():
            self._schedule = self.get_from_database()
            self._last_updated = datetime.datetime.now()
        return self._schedule'''

    '''
    def get_schedule(self):
        print 'get'
        keys = self.manager.inspect(pattern=self._prefix+'*', debug=False)
        data = self.manager.query(keys)
        
        #data = self.redis_manager.get(self._prefix+'*')
        entries = {}
        for k, value in data.iteritems():
            key = k.lstrip(self._prefix)
            value = json.loads(value)
            value['schedule'] = eval(value['schedule'])
            #value['schedule'] = maybe_schedule(value['schedule'])
            entries[key] = self._maybe_entry(key, value)
        print entries 
        return entries

    def set_schedule(self, schedule):
        print 'set'
        for name, v in schedule.iteritems():
            value = json.dumps(v)
            self.manager.conn.set(name, value)
        self.schedule = schedule
    
    schedule = property(get_schedule, set_schedule)

    def sync(self):
        for name, entry in self.schedule.iteritems():
            value = {'task':entry.task,
                     'last_run_at':entry.last_run_at,
                     'total_run_count':entry.total_run_count,
                     'schedule':entry.schedule,
                     'args':entry.args,
                     'kwargs':entry.kwargs,
                     'options':entry.options}
            value = json.dumps(value)
            print name, value
            self.manager.conn.set(name, value)

    def close(self):
        pass
        #self.sync()
        #self._store.close()
    '''

    @property
    def info(self):
        return '<RedisScheduler>'