'''
Created on Apr 2, 2026

@author: darkbk
'''
from re import match
from beehive.common.apimanager import ApiView, ApiManagerError
from beecell.simple import get_attrib

class TaskApiView(ApiView):
    pass

#
# Scheduler
#
class GetSchedulerEntries(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        scheduler = controller.get_scheduler()
        data = scheduler.get_entries()
        resp = [(i[0], i[1].info()) for i in data]
        return resp

class GetSchedulerEntry(TaskApiView):
    def dispatch(self, controller, data, name, *args, **kwargs):
        scheduler = controller.get_scheduler()
        data = scheduler.get_entries(name=name)[0][1]
        if data is not None:
            resp = data.info()
        else:
            raise ApiManagerError("Scheduler entry %s not found" % name, code=404)
        return resp
    
class CreateSchedulerEntry(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        scheduler = controller.get_scheduler()
        name = get_attrib(data, 'name', None)
        task = get_attrib(data, 'task', None)
        args = get_attrib(data, 'args', None)
        kwargs = get_attrib(data, 'kwargs', None)
        options = get_attrib(data, 'options', None)
        relative = get_attrib(data, 'relative', None)
        
        # get schedule
        schedule = get_attrib(data, 'schedule', None)
        
        resp = scheduler.create_update_entry(name, task, schedule, 
                                             args=args, kwargs=kwargs,
                                             options=options, 
                                             relative=relative)        
        return (resp, 202)
    
class DeleteSchedulerEntry(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        scheduler = controller.get_scheduler()
        name = get_attrib(data, 'name', None)
        resp = scheduler.remove_entry(name)        
        return (resp, 202)

#
# Task manager
#
class ManagerPing(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.ping()
        return resp
    
class ManagerStats(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.stats()
        return resp
    
class ManagerReport(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.report()
        return resp
    
class GetTasks(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.get_all_tasks()
        return resp

class GetTasksWithDetail(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.get_all_tasks(details=True)
        return resp    
    
class GetTasksCount(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.count_all_tasks()
        return resp
    
class GetTasksRegistered(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.get_registered_tasks()
        return resp
    
class GetTasksActive(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.get_active_tasks()
        return resp
    
class GetTasksScheduled(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.get_scheduled_tasks()
        return resp
    
class GetTasksReserved(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.get_reserved_tasks()
        return resp
    
class GetTasksRevoked(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.get_revoked_tasks()
        return resp

class QueryTask(TaskApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.query_task(oid)
        return resp
    
class QueryChainedTaskStatus(TaskApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        task_id, failure, state = task_manager.query_chain_status(oid)
        return ([task_id, failure, state], 200)
    
class GetTaskGraph(TaskApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.get_task_graph(oid)
        return resp    
    
class PurgeAllTasks(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        task_manager = controller.get_task_manager()
        resp = task_manager.purge_all_tasks()
        return (resp, 202)
    
class PurgeTasks(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        task_manager = controller.get_task_manager()
        resp = task_manager.purge_tasks()
        return (resp, 202)  
    
class DeleteTask(TaskApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        task_manager = controller.get_task_manager()
        resp = task_manager.delete_task_instance(oid)
        return (resp, 202)  
    
class RevokeTask(TaskApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):
        task_manager = controller.get_task_manager()
        resp = task_manager.revoke_task(oid)
        return (resp, 202)  
    
class SetTaskTimeLimit(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        cmd = get_attrib(data, 'cmd', None)
        # set tasks category time limit
        if cmd == 'time_limit':
            task_name = get_attrib(data, 'name', '')
            limit = get_attrib(data, 'value', 0)
            resp = task_manager.time_limit_task(task_name, limit)
        return resp
    
class RunJobTest(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        job = task_manager.run_jobtest(data)
        return {u'jobid':job.id}
    
class SchedulerAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            ('scheduler/entries', 'GET', GetSchedulerEntries, {}),
            ('scheduler/entry/<name>', 'GET', GetSchedulerEntry, {}),
            ('scheduler/entry', 'POST', CreateSchedulerEntry, {}),
            ('scheduler/entry', 'DELETE', DeleteSchedulerEntry, {}),
        ]

        ApiView.register_api(module, rules)
        
class TaskAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            ('task/ping', 'GET', ManagerPing, {}),
            ('task/stats', 'GET', ManagerStats, {}),
            ('task/report', 'GET', ManagerReport, {}),
            #('task/tasks', 'GET', GetTasks, {}),
            ('task/tasks', 'GET', GetTasksWithDetail, {}),
            ('task/tasks/count', 'GET', GetTasksCount, {}),
            ('task/tasks/registered', 'GET', GetTasksRegistered, {}),
            ('task/tasks/active', 'GET', GetTasksActive, {}),
            ('task/tasks/scheduled', 'GET', GetTasksScheduled, {}),
            ('task/tasks/reserved', 'GET', GetTasksReserved, {}),
            ('task/tasks/revoked', 'GET', GetTasksRevoked, {}),
            ('task/task/<oid>', 'GET', QueryTask, {}),
            #('task/task/<oid>/status', 'GET', QueryChainedTaskStatus, {}),
            ('task/task/<oid>/graph', 'GET', GetTaskGraph, {}),
            ('task/tasks', 'DELETE', PurgeAllTasks, {}),
            ('task/tasks/purge', 'DELETE', PurgeTasks, {}),
            ('task/task/<oid>', 'DELETE', DeleteTask, {}),
            ('task/task/<oid>/revoke', 'DELETE', RevokeTask, {}),
            ('task/task/time_limit', 'PUT', SetTaskTimeLimit, {}),
            ('task/task/jobtest', 'POST', RunJobTest, {})
        ]

        ApiView.register_api(module, rules)