# -*- coding: utf-8 -*-
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

import ujson as json
from datetime import datetime, timedelta

from six import ensure_text

from beecell.db.manager import RedisManagerError
from beecell.simple import get_attrib, truncate
from celery.schedules import crontab
from networkx import DiGraph
from networkx.readwrite import json_graph
from beehive.common.apimanager import ApiController, ApiObject, ApiManagerError
from beehive.module.scheduler.redis_scheduler import RedisScheduleEntry, RedisScheduler
from beehive.common.task.manager import task_scheduler, task_manager
from beehive.common.data import trace
from beehive.common.task.canvas import signature


class SchedulerController(ApiController):
    """Scheduler Module controller."""

    version = "v1.0"

    def __init__(self, module):
        ApiController.__init__(self, module)

        self.child_classes = [Scheduler, TaskManager]

    def add_service_class(self, name, version, service_class):
        self.service_classes.append(service_class)

    '''
    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        """
        # register all child class
        for child_class in self.child_classes:
            child_class(self).init_object()'''

    def get_task_manager(self):
        return TaskManager(self)

    def get_scheduler(self):
        return Scheduler(self)


class Scheduler(ApiObject):
    module = "SchedulerModule"
    objtype = "task"
    objdef = "Scheduler"
    objdesc = "Scheduler"

    def __init__(self, controller):
        ApiObject.__init__(self, controller, oid="", name="", desc="", active="")
        try:
            # self._prefix = task_scheduler.conf.CELERY_REDIS_SCHEDULER_KEY_PREFIX
            # # self._redis = task_scheduler.conf.CELERY_SCHEDULE_BACKEND
            # self._redis = self.controller.redis_scheduler.conn
            # self._pickler = pickle
            # self.objid = '*'
            # # create or get dictionary from redis
            # self.redis_entries = Dict(key=self._prefix, redis=self._redis)

            self.objid = "*"
            self.scheduler = RedisScheduler(task_scheduler, lazy=True)
            self.scheduler.set_redis(self.controller.redis_scheduler)
        except Exception:
            self.logger.warn("", exc_info=1)

    @trace(op="insert")
    def create_update_entry(self, name, task, schedule, args=None, kwargs=None, options={}, relative=None):
        """Create scheduler entry.

        :param name: entry name
        """
        self.verify_permisssions("insert")

        try:
            # new entry
            entry = {
                "name": name,
                "task": task,
                "schedule": schedule,
                "options": options,
            }

            if args is not None:
                entry["args"] = args
            if kwargs is not None:
                entry["kwargs"] = kwargs
            if relative is not None:
                entry["relative"] = relative

            # insert entry in redis
            res = self.scheduler.write_schedule(entry)

            self.logger.info("Create scheduler entry: %s" % entry)
            return {"schedule": name}
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)

    @trace(op="insert")
    def create_update_entry2(self, name, task, schedule, args=None, kwargs=None, options=None, relative=None):
        """Create scheduler entry.

        :param name: entry name
        :param task: The name of the task to execute.
        :param schedule: The frequency of execution. This can be the number of
                         seconds as an integer, a timedelta, or a crontab.
                         You can also define your own custom schedule types,
                         by extending the interface of schedule.
                        {'type':'crontab',
                         'minute':0,
                         'hour':4,
                         'day_of_week':'*',
                         'day_of_month':None,
                         'month_of_year':None}
                        {'type':}
        :param args: Positional arguments (list or tuple).
        :param kwargs: Keyword arguments (dict).
        :param options: Execution options (dict). This can be any argument
                        supported by apply_async(), e.g. exchange, routing_key,
                        expires, and so on.
        :param relative: By default timedelta schedules are scheduled “by the
                         clock”. This means the frequency is rounded to the
                         nearest second, minute, hour or day depending on the
                         period of the timedelta.
                         If relative is true the frequency is not rounded and
                         will be relative to the time when celery beat was started.
        :return:
        :rtype:
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions("insert")

        try:
            if schedule["type"] == "crontab":
                minute = get_attrib(schedule, "minute", "*")
                hour = get_attrib(schedule, "hour", "*")
                day_of_week = get_attrib(schedule, "day_of_week", "*")
                day_of_month = get_attrib(schedule, "day_of_month", "*")
                month_of_year = get_attrib(schedule, "month_of_year", "*")
                schedule = crontab(
                    minute=minute,
                    hour=hour,
                    day_of_week=day_of_week,
                    day_of_month=day_of_month,
                    month_of_year=month_of_year,
                )
            elif schedule["type"] == "timedelta":
                days = get_attrib(schedule, "days", 0)
                seconds = get_attrib(schedule, "seconds", 0)
                minutes = get_attrib(schedule, "minutes", 0)
                hours = get_attrib(schedule, "hours", 0)
                weeks = get_attrib(schedule, "weeks", 0)
                schedule = timedelta(
                    days=days,
                    seconds=seconds,
                    minutes=minutes,
                    hours=hours,
                    weeks=weeks,
                )

            # new entry
            entry = {
                "task": task,
                "schedule": schedule,
                "options": {"queue": task_scheduler.conf.CELERY_TASK_DEFAULT_QUEUE},
            }

            if args is not None:
                entry["args"] = args
            if options is not None:
                entry["options"] = options
            if kwargs is not None:
                entry["kwargs"] = kwargs
            if relative is not None:
                entry["relative"] = relative

            # insert entry in redis
            self.redis_entries[name] = RedisScheduleEntry(**dict(entry, name=name, app=task_scheduler))

            self.logger.info("Create scheduler entry: %s" % entry)
            return {"schedule": name}
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)

    @trace(op="view")
    def get_entries(self, name=None):
        """Get scheduler entries.

        :param name: entry name
        :return: list of (name, entry data) pairs.
        :rtype: list
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions("view")

        try:
            entries = self.scheduler.read_schedule(name)
            self.logger.info("Get scheduler entries: %s" % entries)
            return entries
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=404)

    @trace(op="delete")
    def remove_entry(self, name):
        """Remove scheduler entry.

        :param name: entry name
        :return:
        :rtype:
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions("delete")

        try:
            res = self.scheduler.delete_schedule(name)
            self.logger.info("Remove scheduler entry: %s" % name)
            return True
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)

    @trace(op="delete")
    def remove_entry2(self, name):
        """Remove scheduler entry.

        :param name: entry name
        :return:
        :rtype:
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions("delete")

        try:
            self.logger.warn(self.redis_entries)
            del self.redis_entries[name]
            self.logger.warn(self.redis_entries)
            self.logger.info("Remove scheduler entry: %s" % name)
            return True
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)

    @trace(op="delete")
    def clear_all_entries(self):
        """Clear all scheduler entries.

        :param name: entry name
        :return:
        :rtype:
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions("delete")

        try:
            res = self.redis_entries.clear()
            self.logger.info("Remove all scheduler entries")
            return True
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)
        self.redis_entries.clear()


class TaskManager(ApiObject):
    module = "SchedulerModule"
    objtype = "task"
    objdef = "Manager"
    objdesc = "Task Manager"

    def __init__(self, controller):
        ApiObject.__init__(self, controller, oid="", name="", desc="", active="")

        self.objid = "*"
        try:
            self.hostname = self.celery_broker_queue + "@" + self.api_manager.server_name
            # self.control = task_manager.control.inspect([self.hostname])
            self.prefix = task_manager.conf.CELERY_REDIS_RESULT_KEY_PREFIX
            self.prefix_base = "celery-task-meta"
        except Exception:
            self.control = None
            self.prefix = ""
            self.prefix_base = ""

        self.expire = float(self.api_manager.params.get("expire", 0))

        # print i.memdump()
        # print i.memsample()
        # print i.objgraph()

    @trace(op="use")
    def ping(self):
        """Ping all task manager workers.

        :return:
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions("use")

        try:
            control = task_manager.control
            # res = control.ping([self.hostname], timeout=1.0)
            res = control.ping(timeout=1.0)
            self.logger.debug("Ping task manager workers: %s" % res)
            resp = {}
            for item in res:
                resp.update(item)
            return resp
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)

    @trace(op="use")
    def stats(self):
        """Get stats from all task manager worker

        :return:
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions("use")

        try:
            # control = task_manager.control.inspect([self.hostname], timeout=1.0)
            control = task_manager.control.inspect(timeout=1.0)
            res = control.stats()
            self.logger.debug("Get task manager workers stats: %s" % res)
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)

    @trace(op="use")
    def report(self):
        """Get manager worker report

        :return:
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """

        self.verify_permisssions("use")
        try:
            # control = task_manager.control.inspect([self.hostname], timeout=1.0)
            control = task_manager.control.inspect(timeout=1.0)
            res = control.report()
            self.logger.debug("Get task manager report: %s" % res)
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)

    @trace(op="use")
    def get_active_queues(self):
        """Ping all task manager active queues.

        :return:
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions("use")

        try:
            # control = task_manager.control.inspect([self.hostname], timeout=1.0)
            control = task_manager.control.inspect(timeout=1.0)
            res = control.active_queues()
            self.logger.debug("Get task manager active queues: %s" % res)
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)

    @trace(op="view")
    def get_registered_tasks(self):
        """Get task definitions

        :return:
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions("view")

        try:
            # control = task_manager.control.inspect([self.hostname], timeout=1.0)
            control = task_manager.control.inspect(timeout=1.0)
            res = control.registered()
            if res is None:
                res = []
            self.logger.debug("Get registered tasks: %s" % res)
            return res
        except Exception as ex:
            self.logger.error("No registered tasks found")
            return []

    @trace(op="view")
    def get_all_tasks(self, elapsed=60, ttype=None, details=False):
        """Get all task of type TASK and JOB. Inner job task are not returned.

        :return:
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions("view")

        try:
            res = []
            manager = self.controller.redis_taskmanager
            keys1 = manager.inspect(pattern=self.prefix + "*", debug=False)
            self.logger.debug("Get all %s keys form redis" % len(keys1))

            keys = []
            for k in keys1:
                if self.expire - float(k[2]) < elapsed:
                    keys.append(k)

            self.logger.debug("Get filtered %s keys form redis" % len(keys))

            if details is False:
                for key in keys:
                    key = key[0].lstrip(self.prefix + "-")
                    res.append(key)
            else:
                data = manager.query(keys, ttl=True)
                for key, item in data.items():
                    try:
                        val = json.loads(item[0])
                    except Exception:
                        val = {}
                    ttl = item[1]

                    tasktype = val.get("type", None)
                    val.pop("trace", None)

                    # add time to live
                    val["ttl"] = ttl

                    # add elapsed
                    stop_time = val.get("stop_time", 0)
                    start_time = val.get("start_time", 0)
                    elapsed = 0
                    stop_time_str = 0
                    if start_time is not None and stop_time is not None:
                        elapsed = stop_time - start_time
                        stop_time_str = self.__convert_timestamp(stop_time)

                    # add elapsed
                    val["elapsed"] = elapsed
                    val["stop_time"] = stop_time_str
                    val["start_time"] = self.__convert_timestamp(start_time)

                    # task status
                    available_ttypes = ["JOB", "JOBTASK", "TASK"]
                    ttypes = available_ttypes

                    if ttype is not None and ttype in available_ttypes:
                        ttypes = [ttype]

                    if tasktype in ttypes:
                        res.append(val)

                    # sort task by date
                    res = sorted(res, key=lambda task: task["start_time"])

            self.logger.debug("Get all tasks: %s" % truncate(res))
            return res
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=404)

    @trace(op="view")
    def get_all_tasks2(self, details=False):
        """Get all task of type TASK and JOB. Inner job task are not returned.

        :return:
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions("view")

        try:
            res = []
            manager = self.controller.redis_taskmanager
            keys = manager.inspect(pattern=self.prefix + "*", debug=False)
            self.logger.debug("Get %s keys form redis" % len(keys))
            self.logger.debug("Get %s keys form redis" % truncate(keys))
            if details is False:
                for key in keys:
                    key = key[0].lstrip(self.prefix + "-")
                    res.append(key)
            else:
                data = manager.query(keys, ttl=True)
                for key, item in data.items():
                    try:
                        val = json.loads(item[0])
                    except Exception:
                        val = {}
                    ttl = item[1]

                    tasktype = val.get("type", None)
                    val.pop("trace", None)

                    # add time to live
                    val["ttl"] = ttl

                    # add elapsed
                    stop_time = val.get("stop_time", 0)
                    start_time = val.get("start_time", 0)
                    elapsed = 0
                    stop_time_str = 0
                    if start_time is not None and stop_time is not None:
                        elapsed = stop_time - start_time
                        stop_time_str = self.__convert_timestamp(stop_time)

                    # add elapsed
                    val["elapsed"] = elapsed
                    val["stop_time"] = stop_time_str
                    val["start_time"] = self.__convert_timestamp(start_time)

                    # task status
                    if tasktype in ["JOB", "JOBTASK", "TASK"]:
                        res.append(val)
                        # res = AsyncResult(key, app=task_manager).get()

                    # sort task by date
                    res = sorted(res, key=lambda task: task["start_time"])

            self.logger.debug("Get all tasks: %s" % truncate(res))
            return res
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=404)

    @trace(op="view")
    def count_all_tasks(self):
        """

        :return:
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        self.verify_permisssions("view")

        try:
            res = []
            manager = self.controller.redis_taskmanager
            res = len(manager.inspect(pattern=self.prefix + "*", debug=False))

            self.logger.debug("Count all tasks: %s" % res)
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)

    def __convert_timestamp(self, timestamp):
        """ """
        if isinstance(timestamp, float):
            timestamp = datetime.fromtimestamp(timestamp)
            return ensure_text(timestamp.strftime("%d-%m-%Y %H:%M:%S.%f"))
        return ""

    def __get_redis_task(self, task_id):
        """Get task from redis

        :param task_id: redis key
        :return: task data
        :raise ApiManagerError: if task was not found
        """
        try:
            manager = self.controller.redis_taskmanager
            task_data, task_ttl = manager.get_with_ttl(self.prefix + task_id, max_retry=3, delay=0.01)
        except RedisManagerError as ex:
            raise ApiManagerError("Task %s not found" % task_id, code=404)

        return task_data, task_ttl

    def _get_task_info(self, task_id):
        """ """
        manager = self.controller.redis_taskmanager
        # keys = manager.inspect(pattern=self.prefix + task_id, debug=False)
        # data = manager.query(keys, ttl=True)[self.prefix + task_id]
        task_data, task_ttl = self.__get_redis_task(task_id)

        # get task info and time to live
        # val = json.loads(data[0])
        # ttl = data[1]
        val = json.loads(task_data)
        ttl = task_ttl

        # add time to live
        val["ttl"] = ttl

        # add elapsed
        stop_time = val.get("stop_time", 0)
        start_time = val.get("start_time", 0)
        elapsed = 0
        stop_time_str = 0
        if start_time is not None and stop_time is not None:
            elapsed = stop_time - start_time
            stop_time_str = self.__convert_timestamp(stop_time)

        # add elapsed
        val["elapsed"] = elapsed
        val["stop_time"] = stop_time_str
        val["start_time"] = self.__convert_timestamp(start_time)
        # val['trace'] = None

        # get child jobs
        jobs = val.get("jobs", [])
        job_list = []
        if jobs is not None and len(jobs) > 0:
            for job in jobs:
                job_list.append(self.query_task(job))
        val["jobs"] = job_list
        return val

    def _get_task_graph(self, task, graph, index=1):
        """Get task graph.

        :return: Dictionary with task node and link
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            child_ids = task["children"]
            child_index = index + 1
            for child_id in child_ids:
                try:
                    child = self._get_task_info(child_id)
                    if len(child["children"]) == 0:
                        task_type = "end"
                    else:
                        task_type = "inner"
                    graph.add_node(
                        child_id,
                        id=child["task_id"],
                        label=child["name"].split(".")[-1],
                        type=task_type,
                        details=child,
                    )
                    graph.add_edge(task["task_id"], child_id)

                    # call get_task_graph with task child
                    self._get_task_graph(child, graph, child_index)
                    child_index += 1
                    self.logger.debug("Get child task %s" % child_id)
                except Exception:
                    self.logger.warn("Child task %s does not exist" % child_id, exc_info=1)

            return graph
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)

    def _get_task_childs(self, childs_index, task):
        """Get task childs.

        :param childs_index: dict with task references
        :param task: task to explore
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        try:
            child_ids = task.pop("children")
            self.logger.debug2("Get task %s children: %s" % (task["task_id"], child_ids))
            if child_ids is not None:
                for child_id in child_ids:
                    try:
                        if child_id in childs_index:
                            continue

                        child = self._get_task_info(child_id)
                        childs_index[child_id] = child
                        self._get_task_childs(childs_index, child)
                    except Exception:
                        self.logger.warn("Child task %s does not exist" % child_id)
        except Exception as ex:
            raise ApiManagerError(ex, code=400)

    @trace(op="view")
    def query_task(self, task_id, chain=True):
        """Get task info. If task type JOB return graph composed by all the job childs.

        :param task_id: id of the celery task
        :param chain: if True get all task chain
        :return:
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("view")

        res = []
        task_data, task_ttl = self.__get_redis_task(task_id)

        try:
            # get task info and time to live
            val = json.loads(task_data)
            ttl = task_ttl

            tasktype = val.get("type", "JOB")

            # add time to live
            val["ttl"] = ttl

            # JOB
            if tasktype == "JOB":
                stop_time = val.get("stop_time", 0)
                start_time = val.get("start_time", 0)
                elapsed = 0
                stop_time_str = 0
                if start_time is not None and stop_time is not None:
                    elapsed = stop_time - start_time
                    stop_time_str = self.__convert_timestamp(stop_time)

                # add elapsed
                val["elapsed"] = elapsed
                val["stop_time"] = stop_time_str
                val["start_time"] = self.__convert_timestamp(start_time)

                if chain is True:
                    try:
                        # get job childs
                        childrens = val.pop("children", [])
                        if len(childrens) > 0:
                            first_child_id = childrens[0]
                            first_child = self._get_task_info(first_child_id)
                            first_child["inner_type"] = "start"
                            childs_index = {first_child_id: first_child}
                            self._get_task_childs(childs_index, first_child)

                            # sort childs by date
                            childs = sorted(
                                childs_index.values(),
                                key=lambda task: task["start_time"],
                            )

                            # get childs trace
                            trace = []
                            for c in childs:
                                for t in c.pop("trace"):
                                    trace.append((t[0], c["name"], c["task_id"], t[1]))
                            # sort trace
                            val["trace"] = sorted(trace, key=lambda row: row[0])
                            val["children"] = childs
                    except Exception:
                        self.logger.warn("", exc_info=1)
                        val["children"] = None
            else:
                val["children"] = None

            res = val
            self.logger.debug("Get task %s info: %s" % (task_id, truncate(res)))
            return res
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)

    @trace(op="view")
    def get_task_graph(self, task_id):
        """Get job task child graph

        :return:
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("view")

        graph_data = None

        task_data, task_ttl = self.__get_redis_task(task_id)

        try:
            # get task info and time to live
            val = json.loads(task_data)

            childs = val["children"]
            tasktype = val["type"]

            # JOB
            if tasktype == "JOB":
                # create graph
                graph = DiGraph(name="Task %s child graph" % val["name"])
                # populate graph
                child = self._get_task_info(childs[0])
                graph.add_node(
                    child["task_id"],
                    id=child["task_id"],
                    label=child["name"].split(".")[-1],
                    type="start",
                    details=child,
                )
                self._get_task_graph(child, graph)
                # get graph
                graph_data = json_graph.node_link_data(graph)
            else:
                raise Exception("Task %s is not of type JOB" % task_id)

            res = graph_data
            self.logger.debug("Get task %s graph: %s" % (task_id, truncate(res)))
            return res
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=404)

    @trace(op="delete")
    def delete_task_instances(self):
        """

        :return:
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("delete")

        try:
            res = []
            manager = self.controller.redis_taskmanager
            res = manager.delete(pattern=self.prefix + "*")

            self.logger.debug("Purge all tasks: %s" % res)
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=400)

        self.manager.delete(pattern=self.prefix + "*")

    def _delete_task_child(self, task_id):
        """Delete task child instances from result db."""
        manager = self.controller.redis_taskmanager

        # res = AsyncResult(task_id, app=task_manager)

        try:
            res = manager.server.get(self.prefix + task_id)
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=404)

        # get children
        if res is not None:
            res = json.loads(res)
            childrens = res.get("children", [])
            for child_id in childrens:
                self._delete_task_child(child_id)
                task_name = self.prefix + child_id
                res = manager.delete(pattern=task_name)
                self.logger.debug("Delete task instance %s: %s" % (child_id, res))
        return True

    @trace(op="delete")
    def delete_task_instance(self, task_id, propagate=True):
        """Delete task instance result from results db.

        :param task_id: id of the task instance
        :param propagate: if True delete all the childs
        :return:
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("delete")

        try:
            # delete childs
            if propagate is True:
                self._delete_task_child(task_id)

            # delete task instance
            manager = self.controller.redis_taskmanager
            task_name = self.prefix + task_id
            res = manager.delete(pattern=task_name)
            self.logger.debug("Delete task instance %s: %s" % (task_id, res))
            return res
        except Exception as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex, code=400)

    @trace(op="view")
    def get_active_queue(self):
        """

        :return:
        :rtype: dict
        :raises ApiManagerError: raise :class:`.ApiManagerError`
        """
        # verify permissions
        self.verify_permisssions("view")

        try:
            control = task_manager.control.inspect([self.hostname])
            res = control.active_queues()
            self.logger.debug("Get task manager active queue: %s" % (res))
            return res
        except Exception as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex, code=404)

    #
    # test jobs
    #
    @trace(op="insert")
    def run_jobtest(self, params):
        """Run jobtest task

        :param params: task input params

                        {'x':..,
                         'y':..,
                         'numbers':[],
                         'mul_numbers':[]}

        :return: celery task instance
        :rtype: Task
        :raises ApiManagerError if query empty return error.
        """
        # verify permissions
        self.controller.check_authorization(self.objtype, self.objdef, None, "insert")

        params.update(self.get_user())
        task = signature(
            "beehive.module.scheduler.tasks.jobtest",
            (self.objid, params),
            app=task_manager,
            queue=self.celery_broker_queue,
        )
        job = task.apply_async()

        # save job
        add_job = getattr(self.controller.module.get_related_controller(), "add_job", None)
        if add_job is not None:
            add_job(job.id, "jobtest", params)

        return job
