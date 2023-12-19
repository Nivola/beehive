# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

import copy
import heapq
import logging
import ujson as json
from celery.schedules import crontab
from beecell.db.manager import RedisManager
from celery.beat import Scheduler
from datetime import timedelta, datetime
from celery.beat import ScheduleEntry, event_t
from beecell.simple import format_date


logger = logging.getLogger(__name__)


class RedisScheduleEntry(ScheduleEntry):
    """An entry in the scheduler.

    :param str name: see :attr:`name`.
    :param celery.schedules.schedule schedule: see :attr:`schedule`.
    :param Tuple args: see :attr:`args`.
    :param Dict kwargs: see :attr:`kwargs`.
    :param Dict options: see :attr:`options`.
    :param datetime.datetime last_run_at: see :attr:`last_run_at`.
    :param int total_run_count: see :attr:`total_run_count`.
    :param bool relative: Is the time relative to when the server starts?
    """

    def info(self):
        """ """
        res = {
            "name": self.name,
            "task": self.task,
            "schedule": str(self.schedule),
            "args": self.args,
            "kwargs": self.kwargs,
            "options": self.options,
            "last_run_at": format_date(self.last_run_at),
            "total_run_count": self.total_run_count,
        }
        return res

    @staticmethod
    def create(
        app,
        name,
        task,
        schedule,
        args=None,
        kwargs=None,
        options=None,
        relative=None,
        last_run_at=None,
        total_run_count=None,
    ):
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
            if schedule["type"] == "crontab":
                minute = schedule.get("minute", "*")
                hour = schedule.get("hour", "*")
                day_of_week = schedule.get("day_of_week", "*")
                day_of_month = schedule.get("day_of_month", "*")
                month_of_year = schedule.get("month_of_year", "*")
                schedule = crontab(
                    minute=str(minute),
                    hour=str(hour),
                    day_of_week=str(day_of_week),
                    day_of_month=str(day_of_month),
                    month_of_year=str(month_of_year),
                )
            elif schedule["type"] == "timedelta":
                days = schedule.get("days", 0)
                seconds = schedule.get("seconds", 0)
                minutes = schedule.get("minutes", 0)
                hours = schedule.get("hours", 0)
                weeks = schedule.get("weeks", 0)
                schedule = timedelta(
                    days=days,
                    seconds=seconds,
                    minutes=minutes,
                    hours=hours,
                    weeks=weeks,
                )

            # new entry
            entry = {
                "name": name,
                "task": task,
                "schedule": schedule,
                "total_run_count": total_run_count,
            }

            if args is not None:
                entry["args"] = args
            if options is not None:
                entry["options"] = options
            if kwargs is not None:
                entry["kwargs"] = kwargs
            if relative is not None:
                entry["relative"] = relative
            if last_run_at is not None:
                entry["last_run_at"] = datetime.strptime(last_run_at, "%Y-%m-%dT%H:%M:%SZ")

            res = RedisScheduleEntry(**dict(entry, name=name, app=app))

            return res
        except Exception as ex:
            logger.error(ex, exc_info=True)
            raise


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
            self._redis_manager = RedisManager(self.app.conf.scheduler_backend)
        self._prefix = self.app.conf.scheduler_key_prefix

    def open_schedule(self, with_last_run_at=False):
        try:
            # get all the schedules
            keys = self._redis_manager.inspect(pattern=self._prefix + ".*", debug=False)
            logger.debug("Get %s schedule keys form redis" % keys)

            data = self._redis_manager.query(keys, ttl=True)
            self._store = {}
            for key, item in data.items():
                try:
                    val = json.loads(item[0])
                except Exception:
                    logger.warning("", exc_info=True)
                    val = {}
                name = val.get("name")
                options = val.get("options", {})
                options.update({"queue": self.app.conf.task_default_queue})

                if with_last_run_at is True:
                    self._store[name] = self.Entry.create(
                        self.app,
                        name,
                        val.get("task"),
                        val.get("schedule"),
                        args=val.get("args"),
                        kwargs=val.get("kwargs"),
                        options=options,
                        relative=val.get("relative"),
                        total_run_count=val.get("total_run_count"),
                        last_run_at=val.get("last_run_at"),
                    )
                else:
                    self._store[name] = self.Entry.create(
                        self.app,
                        name,
                        val.get("task"),
                        val.get("schedule"),
                        args=val.get("args"),
                        kwargs=val.get("kwargs"),
                        options=options,
                        relative=val.get("relative"),
                        total_run_count=val.get("total_run_count"),
                    )
            logger.debug("Get schedules from redis: %s" % self._store)
        except Exception as exc:
            logger.error(exc, exc_info=True)
            self._store = None
        return self._store

    def write_schedule(self, schedule):
        try:
            self._get_redis()
            # set queue
            schedule["options"].update({"queue": self.app.conf.task_default_queue})

            key = self._prefix + "." + schedule.get("name")
            res = self._redis_manager.set(key, json.dumps(schedule))
            logger.debug("Create schedule %s to redis key %s: %s" % (schedule.get("name"), key, res))
        except Exception as exc:
            logger.error(exc, exc_info=True)
            raise
        return res

    def delete_schedule(self, name):
        try:
            self._get_redis()
            key = self._prefix + "." + name
            res = self._redis_manager.delete(key)
            logger.debug("Delete schedule %s from redis key %s: %s" % (name, key, res))
        except Exception as exc:
            logger.error(exc, exc_info=True)
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
            logger.error(exc, exc_info=True)
            entries = []
        return entries

    def setup_schedule(self):
        try:
            self._get_redis()
            self._store = self.open_schedule()
            self._store.keys()
        except Exception as exc:
            logger.error(exc, exc_info=True)
            self._store = None

    def get_schedule(self):
        res = self._store
        # logger.warning('Get schedule: %s' % res)
        return res

    def set_schedule(self, schedule):
        self._store = schedule
        # logger.warning('Set schedule: %s' % schedule)

    schedule = property(get_schedule, set_schedule)

    def sync(self):
        if self._store is not None:
            self._store = self.open_schedule()

    def reserve(self, entry):
        new_entry = next(entry)
        key = self._prefix + "." + new_entry.name
        redis_entry = self._redis_manager.get(key)
        if redis_entry is not None:
            redis_entry = json.loads(redis_entry)
            redis_entry["last_run_at"] = format_date(new_entry.last_run_at)
            redis_entry["total_run_count"] = new_entry.total_run_count
            res = self._redis_manager.set(key, json.dumps(redis_entry))
        return new_entry

    def close(self):
        self.sync()

    @property
    def info(self):
        return "RedisScheduler"
