'''
Created on Apr 2, 2026

@author: darkbk
'''
from beecell.simple import get_value
from beehive.common.apimanager import ApiView, ApiManagerError

class TaskApiView(ApiView):
    pass

#
# Scheduler
#
class GetSchedulerEntries(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        scheduler = controller.get_scheduler()
        data = scheduler.get_entries()
        res = [i[1].info() for i in data]
        resp = {
            u'schedules':res,
            u'count':len(res)
        }
        return resp

class GetSchedulerEntry(TaskApiView):
    def dispatch(self, controller, data, name, *args, **kwargs):
        scheduler = controller.get_scheduler()
        data = scheduler.get_entries(name=name)[0][1]
        if data is not None:
            res = data.info()
        else:
            raise ApiManagerError(u'Scheduler entry %s not found' % name, code=404)
        resp = {
            u'schedule':res
        }
        return resp
    
class CreateSchedulerEntry(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        scheduler = controller.get_scheduler()
        data = get_value(data, u'schedule', None, exception=True)
        name = get_value(data, u'name', None, exception=True)
        task = get_value(data, u'task', None, exception=True)
        args = get_value(data, u'args', None)
        kwargs = get_value(data, u'kwargs', None)
        options = get_value(data, u'options', None)
        relative = get_value(data, u'relative', None)
        
        # get schedule
        schedule = get_value(data, u'schedule', None, exception=True)
        
        resp = scheduler.create_update_entry(name, task, schedule, 
                                             args=args, kwargs=kwargs,
                                             options=options, 
                                             relative=relative)        
        return (resp, 202)
    
class DeleteSchedulerEntry(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        scheduler = controller.get_scheduler()
        name = get_value(data, u'name', None, exception=True)
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
    
class GetTasksDefinition(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        res = task_manager.get_registered_tasks()
        resp = {
            u'task-definitions':res,
            u'count':len(res)
        }
        return resp    

class GetTasksWithDetail(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        res = task_manager.get_all_tasks(details=True)
        resp = {
            u'task-instances':res,
            u'count':len(res)
        }        
        return resp
    
class GetTasksCount(TaskApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.count_all_tasks()
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
        res = task_manager.query_task(oid)
        resp = {u'task-instance':res}
        return resp
    
class QueryTaskStatus(TaskApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.query_task_status(oid)
        return resp
    
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
        cmd = get_value(data, 'cmd', None)
        # set tasks category time limit
        if cmd == 'time_limit':
            task_name = get_value(data, 'name', '')
            limit = get_value(data, 'value', 0)
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
            (u'scheduler/entries', 'GET', GetSchedulerEntries, {}),
            (u'scheduler/entry/<name>', 'GET', GetSchedulerEntry, {}),
            (u'scheduler/entry', 'POST', CreateSchedulerEntry, {}),
            (u'scheduler/entry', 'DELETE', DeleteSchedulerEntry, {}),
        ]

        ApiView.register_api(module, rules)
        
class TaskAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            (u'worker/ping', u'GET', ManagerPing, {}),
            (u'worker/stats', u'GET', ManagerStats, {}),
            (u'worker/report', u'GET', ManagerReport, {}),
            #(u'worker/tasks', u'GET', GetTasks, {}),
            (u'worker/tasks', u'GET', GetTasksWithDetail, {}),
            (u'worker/tasks/count', u'GET', GetTasksCount, {}),
            (u'worker/tasks/definitions', u'GET', GetTasksDefinition, {}),
            #(u'worker/tasks/active', u'GET', GetTasksActive, {}),
            #(u'worker/tasks/scheduled', u'GET', GetTasksScheduled, {}),
            #(u'worker/tasks/reserved', u'GET', GetTasksReserved, {}),
            #(u'worker/tasks/revoked', u'GET', GetTasksRevoked, {}),
            (u'worker/tasks/<oid>', u'GET', QueryTask, {}),
            (u'worker/tasks/<oid>/status', u'GET', QueryTaskStatus, {}),
            (u'worker/tasks/<oid>/graph', u'GET', GetTaskGraph, {}),
            (u'worker/tasks', u'DELETE', PurgeAllTasks, {}),
            (u'worker/tasks/purge', u'DELETE', PurgeTasks, {}),
            (u'worker/tasks/<oid>', u'DELETE', DeleteTask, {}),
            (u'worker/tasks/<oid>/revoke', u'DELETE', RevokeTask, {}),
            #(u'worker/tasks/time-limit', u'PUT', SetTaskTimeLimit, {}),
            (u'worker/tasks/test', u'POST', RunJobTest, {}),
        ]

        ApiView.register_api(module, rules)