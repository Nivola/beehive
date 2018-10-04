"""
Created on Nov 13, 2015

@author: darkbk
"""
import logging
import ujson as json
from beecell.db.manager import RedisManager
from celery.beat import Scheduler
from datetime import timedelta, datetime
from celery.schedules import maybe_schedule, crontab, schedule as interval
from celery.beat import ScheduleEntry 
from celery.five import items
from kombu.utils import reprcall
import redis_collections
from beecell.simple import format_date
#import pickle


logger = logging.getLogger(__name__)


class RedisScheduleEntry(ScheduleEntry):
    # """An entry in the scheduler.
    #
    # :keyword name: see :attr:`name`.
    # :keyword schedule: see :attr:`schedule`.
    # :keyword args: see :attr:`args`.
    # :keyword kwargs: see :attr:`kwargs`.
    # :keyword options: see :attr:`options`.
    # :keyword last_run_at: see :attr:`last_run_at`.
    # :keyword total_run_count: see :attr:`total_run_count`.
    # :keyword relative: Is the time relative to when the server starts?
    #
    # """
    #
    # #: The task name
    # name = None
    #
    # #: The schedule (run_every/crontab)
    # schedule = None
    #
    # #: Positional arguments to apply.
    # args = None
    #
    # #: Keyword arguments to apply.
    # kwargs = None
    #
    # #: Task execution options.
    # options = None
    #
    # #: The time and date of when this task was last scheduled.
    # last_run_at = None
    #
    # #: Total number of times this task has been scheduled.
    # total_run_count = 0
    #
    # def __init__(self, name=None, task=None, last_run_at=None,
    #              total_run_count=None, schedule=None, args=(), kwargs={},
    #              options={}, relative=False, app=None):
    #     self.app = app
    #     self.name = name
    #     self.task = task
    #     self.args = args
    #     self.kwargs = kwargs
    #     self.options = options
    #     self.schedule = maybe_schedule(schedule, relative, app=self.app)
    #     self.last_run_at = last_run_at or self.default_now()
    #     self.total_run_count = total_run_count or 0
    #
    # def default_now(self):
    #     return self.schedule.now() if self.schedule else self.app.now()
    #
    # def _next_instance(self, last_run_at=None):
    #     """Return a new instance of the same class, but with
    #     its date and count fields updated."""
    #     return self.__class__(**dict(
    #         self,
    #         last_run_at=last_run_at or self._default_now(),
    #         total_run_count=self.total_run_count + 1,
    #     ))
    # __next__ = next = _next_instance  # for 2to3
    #
    # def __reduce__(self):
    #     return self.__class__, (
    #         self.name, self.task, self.last_run_at, self.total_run_count,
    #         self.schedule, self.args, self.kwargs, self.options,
    #     )
    #
    # def update(self, other):
    #     """Update values from another entry.
    #
    #     Does only update "editable" fields (task, schedule, args, kwargs,
    #     options).
    #
    #     """
    #     self.__dict__.update({'task': other.task, 'schedule': other.schedule,
    #                           'args': other.args, 'kwargs': other.kwargs,
    #                           'options': other.options})
    #
    # def is_due(self):
    #     """See :meth:`~celery.schedule.schedule.is_due`."""
    #     return self.schedule.is_due(self.last_run_at)
    #
    # def __iter__(self):
    #     return iter(items(vars(self)))
    #
    # def __repr__(self):
    #     return '<Entry: {0.name} {call} {0.schedule}'.format(
    #         self,
    #         call=reprcall(self.task, self.args or (), self.kwargs or {}),
    #     )
        
    def info(self):
        """ """
        res = {'name': self.name,
               'task': self.task,
               'schedule': str(self.schedule),
               'args': self.args,
               'kwargs': self.kwargs,
               'options': self.options,
               'last_run_at': format_date(self.last_run_at),
               'total_run_count': self.total_run_count}
        return res

    @staticmethod
    def create(app, name, task, schedule, args=None, kwargs=None, options=None, relative=None, last_run_at=None,
               total_run_count=None):
        """Create scheduler entry.

        :param app: entry scheduler reference
        :param name: entry name
        :param task: The name of the task to execute.
        :param schedule: The frequency of execution. This can be the number of seconds as an integer, a timedelta,
            or a crontab. You can also define your own custom schedule types, by extending the interface of schedule.

                        {'type':'crontab',
                         'minute':0,
                         'hour':4,
                         'day_of_week':'*',
                         'day_of_month':None,
                         'month_of_year':None}
                        {'type':}

        :param args: Positional arguments (list or tuple).
        :param kwargs: Keyword arguments (dict).
        :param options: Execution options (dict). This can be any argument supported by apply_async(), e.g. exchange,
            routing_key, expires, and so on.
        :param relative: By default timedelta schedules are scheduled "by the clock". This means the frequency is
            rounded to the nearest second, minute, hour or day depending on the period of the timedelta.
            If relative is true the frequency is not rounded and will be relative to the time when celery beat was
            started.
        :param last_run_at: The time and date of when this task was last scheduled.
        :param total_run_count: Total number of times this task has been scheduled.
        :return:
        :rtype:
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            if schedule[u'type'] == u'crontab':
                minute = schedule.get(u'minute', u'*')
                hour = schedule.get(u'hour', u'*')
                day_of_week = schedule.get(u'day_of_week', u'*')
                day_of_month = schedule.get(u'day_of_month', u'*')
                month_of_year = schedule.get(u'month_of_year', u'*')
                schedule = crontab(minute=minute,
                                   hour=hour,
                                   day_of_week=day_of_week,
                                   day_of_month=day_of_month,
                                   month_of_year=month_of_year)
            elif schedule[u'type'] == u'timedelta':
                days = schedule.get(u'days', 0)
                seconds = schedule.get(u'seconds', 0)
                minutes = schedule.get(u'minutes', 0)
                hours = schedule.get(u'hours', 0)
                weeks = schedule.get(u'weeks', 0)
                schedule = timedelta(days=days,
                                     seconds=seconds,
                                     minutes=minutes,
                                     hours=hours,
                                     weeks=weeks)

            # new entry
            entry = {
                u'name': name,
                u'task': task,
                u'schedule': schedule,
                u'total_run_count': total_run_count
            }

            if args is not None:
                entry[u'args'] = args
            if options is not None:
                entry[u'options'] = options
            if kwargs is not None:
                entry[u'kwargs'] = kwargs
            if relative is not None:
                entry[u'relative'] = relative
            if last_run_at is not None:
                entry[u'last_run_at'] = datetime.strptime(last_run_at, u'%Y-%m-%dT%H:%M:%SZ')

            res = RedisScheduleEntry(**dict(entry, name=name, app=app))

            # logger.info(u'Create entry: %s' % res)
            return res
        except Exception as ex:
            logger.error(ex, exc_info=1)
            raise


class RedisScheduler2(Scheduler):
    Entry = RedisScheduleEntry

    def __init__(self, app, schedule={}, max_interval=None, Publisher=None, lazy=False, sync_every_tasks=None,
                 **kwargs):
        # self.schedule_filename = kwargs.get('schedule_filename')
        redis_uri = app.conf.CELERY_SCHEDULE_BACKEND
        # set redis manager
        self.manager = RedisManager(redis_uri)
        # keys = self.manager.inspect(pattern='*', debug=False)
        
        self._prefix = app.conf.CELERY_REDIS_SCHEDULER_KEY_PREFIX
        
        self._schedule = redis_collections.Dict(key=self._prefix, redis=self.manager.conn)
        Scheduler.__init__(self, app, schedule=schedule, max_interval=max_interval, Publisher=Publisher,
                           lazy=lazy, sync_every_tasks=sync_every_tasks, **kwargs)

    def update_from_dict(self, dict_):
        self.schedule.update({
            name: self._maybe_entry(name, entry)
            for name, entry in items(dict_)
        })
    
    def get_schedule(self):
        logger.warn('GET', self._schedule)
        return self._schedule

    def set_schedule(self, schedule):
        logger.warn('SET', schedule)
        self.data = schedule
        
    schedule = property(get_schedule, set_schedule)
    
    def setup_schedule(self):
        # self.install_default_entries(self.schedule)
        schedule = self.app.conf.CELERYBEAT_SCHEDULE
        schedule.update(self._schedule)
        logger.warn(u'Setup schedules: %s' % schedule)
        self.update_from_dict(schedule)

    @property
    def info(self):
        return u'<RedisScheduler>'


class RedisScheduler(Scheduler):
    Entry = RedisScheduleEntry

    _store = None
    _redis_manager = None
    _prefix = None

    #: How often to sync the schedule (3 minutes by default)
    sync_every = 10

    #: How many tasks can be called before a sync is forced.
    sync_every_tasks = None

    def __init__(self, *args, **kwargs):
        Scheduler.__init__(self, *args, **kwargs)

    def set_redis(self, redis_manager):
        self._redis_manager = redis_manager

    def _get_redis(self):
        # set redis manager
        if self._redis_manager is None:
            self._redis_manager = RedisManager(self.app.conf.CELERY_SCHEDULE_BACKEND)
        self._prefix = self.app.conf.CELERY_REDIS_SCHEDULER_KEY_PREFIX

    def open_schedule(self, with_last_run_at=False):
        try:
            # get all the schedules
            keys = self._redis_manager.inspect(pattern=self._prefix + u'.*', debug=False)
            logger.debug(u'Get %s schedule keys form redis' % keys)

            data = self._redis_manager.query(keys, ttl=True)
            self._store = {}
            for key, item in data.iteritems():
                try:
                    val = json.loads(item[0])
                except:
                    logger.warn(u'', exc_info=1)
                    val = {}
                name = val.get(u'name')
                options = val.get(u'options', {})
                options.update({u'queue': self.app.conf.CELERY_TASK_DEFAULT_QUEUE})
                if with_last_run_at is True:
                    self._store[name] = self.Entry.create(self.app, name, val.get(u'task'), val.get(u'schedule'),
                                                          args=val.get(u'args'), kwargs=val.get(u'kwargs'),
                                                          options=options, relative=val.get(u'relative'),
                                                          total_run_count=val.get(u'total_run_count'),
                                                          last_run_at=val.get(u'last_run_at'))
                else:
                    self._store[name] = self.Entry.create(self.app, name, val.get(u'task'), val.get(u'schedule'),
                                                          args=val.get(u'args'), kwargs=val.get(u'kwargs'),
                                                          options=options, relative=val.get(u'relative'),
                                                          total_run_count=val.get(u'total_run_count'))
            logger.debug(u'Get schedules from redis: %s' % self._store)
        except Exception:
            logger.error(u'', exc_info=1)
            self._store = None
        return self._store

    def write_schedule(self, schedule):
        try:
            self._get_redis()
            # set queue
            schedule[u'options'].update({u'queue': self.app.conf.CELERY_TASK_DEFAULT_QUEUE})

            key = self._prefix + u'.' + schedule.get(u'name')
            res = self._redis_manager.set(key, json.dumps(schedule))
            logger.debug(u'Create schedule %s to redis key %s: %s' % (schedule.get(u'name'), key, res))
        except Exception as exc:
            logger.error(exc, exc_info=1)
            raise
        return res

    def delete_schedule(self, name):
        try:
            self._get_redis()
            key = self._prefix + u'.' + name
            res = self._redis_manager.delete(key)
            logger.debug(u'Delete schedule %s from redis key %s: %s' % (name, key, res))
        except Exception as exc:
            logger.error(exc, exc_info=1)
            raise
        return res

    def read_schedule(self, name=None):
        try:
            self._get_redis()
            entries = self.open_schedule(with_last_run_at=True)
            if name is not None:
                entries = [entries.get(name)]
            else:
                entries = entries.values()
        except Exception as exc:
            logger.error(exc, exc_info=1)
            entries = []
        return entries

    def setup_schedule(self):
        try:
            self._get_redis()
            self._store = self.open_schedule()
            self._store.keys()
        except Exception as exc:
            logger.error(exc, exc_info=1)
            self._store = None

    def get_schedule(self):
        res = self._store
        # logger.warn(u'Get schedule: %s' % res)
        return res

    def set_schedule(self, schedule):
        self._store = schedule
        # logger.warn(u'Set schedule: %s' % schedule)

    schedule = property(get_schedule, set_schedule)

    def sync(self):
        # new_store = self.open_schedule()
        # new_store.update(self._store)
        if self._store is not None:
            self._store = self.open_schedule()

    def reserve(self, entry):
        # new_entry = self.schedule[entry.name] = next(entry)
        new_entry = next(entry)
        key = self._prefix + u'.' + new_entry.name
        redis_entry = self._redis_manager.get(key)
        if redis_entry is not None:
            redis_entry = json.loads(redis_entry)
            redis_entry[u'last_run_at'] = format_date(new_entry.last_run_at)
            redis_entry[u'total_run_count'] = new_entry.total_run_count
            res = self._redis_manager.set(key, json.dumps(redis_entry))
        return new_entry

    def close(self):
        self.sync()

    @property
    def info(self):
        return u'RedisScheduler'
