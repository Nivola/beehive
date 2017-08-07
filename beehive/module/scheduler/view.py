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
    def get(self, controller, data, *args, **kwargs):
        """
        List scheduler entries
        Call this api to list all the scheduler entries
        ---
        deprecated: false
        tags:
          - scheduler
        security:
          - ApiKeyAuth: []
          - OAuth2: [auth, beehive]
        responses:
          500:
            $ref: "#/responses/InternalServerError"
          400:
            $ref: "#/responses/BadRequest"
          401:
            $ref: "#/responses/Unauthorized"
          408:
            $ref: "#/responses/Timeout"
          415:
            $ref: "#/responses/UnsupportedMediaType"
          default: 
            $ref: "#/responses/Default"             
          200:
            description: Entries list
            schema:
              type: object
              required: [schedules, count]
              properties:
                count:
                  type: integer
                  example: 1
                schedules:
                  type: array
                  items:
                    type: object
                    required: [args, kwargs, last_run_at, name, options, schedule, task, total_run_count]
                    properties:
                      args:
                        type: array
                      kwargs:
                        type: object
                      last_run_at:
                        type: integer
                        example: 1459755371
                      name:
                        type: string
                        example: discover
                      options:
                        type: object
                      schedule:
                        type: string
                        example: "<freq: 5.00 minutes>"
                      task:
                        type: string
                        example: tasks.discover_vsphere
                      total_run_count:
                        type: integer
                        example: 679
        """
        scheduler = controller.get_scheduler()
        data = scheduler.get_entries()
        res = [i[1].info() for i in data]
        resp = {
            u'schedules':res,
            u'count':len(res)
        }
        return resp

class GetSchedulerEntry(TaskApiView):
    def get(self, controller, data, name, *args, **kwargs):
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
    def post(self, controller, data, *args, **kwargs):
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
    def delete(self, controller, data, *args, **kwargs):    
        scheduler = controller.get_scheduler()
        name = get_value(data, u'name', None, exception=True)
        resp = scheduler.remove_entry(name)        
        return (resp, 202)

#
# Task manager
#
class ManagerPing(TaskApiView):
    def get(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.ping()
        return resp
    
class ManagerStats(TaskApiView):
    def get(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.stats()
        return resp
    
class ManagerReport(TaskApiView):
    def get(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.report()
        return resp
    
class GetTasksDefinition(TaskApiView):
    def get(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        res = task_manager.get_registered_tasks()
        resp = {
            u'task-definitions':res,
            u'count':len(res)
        }
        return resp    

class GetAllTasks(TaskApiView):
    def get(self, controller, data, *args, **kwargs):
        """
        List task instances
        Call this api to list all the task instances
        ---
        deprecated: false
        tags:
          - Task manager api
        security:
          - ApiKeyAuth: []
          - OAuth2: [auth, beehive]
        responses:
          500:
            $ref: "#/responses/InternalServerError"
          400:
            $ref: "#/responses/BadRequest"
          401:
            $ref: "#/responses/Unauthorized"
          408:
            $ref: "#/responses/Timeout"
          415:
            $ref: "#/responses/UnsupportedMediaType"
          default: 
            $ref: "#/responses/Default"             
          200:
            description: Task instances list
            schema:
              type: object
              required: [task-instances, count]
              properties:
                count:
                  type: integer
                  example: 1
                task-instances:
                  type: array
                  items:
                    type: object
                    required: [status, traceback, jobs, name, task_id, kwargs, start_time, stop_time, args, worker, elapsed, result, ttl, type, children]
                    properties:
                      status:
                        type: string
                        example: SUCCESS
                      traceback:
                        type: array
                        items:
                          type: string
                          example: error error
                      jobs:
                        type: array
                        items:
                          type: string
                          example: c518fa8b-1247-4f9f-9d73-785bcc24b8c7
                      name:
                        type: string
                        example: beehive.module.scheduler.tasks.jobtest
                      task_id:
                        type: string
                        example: c518fa8b-1247-4f9f-9d73-785bcc24b8c7
                      kwargs:
                        type: object
                        properties:
                          user:
                            type: string
                            example: admin@local
                          identity:
                            type: string
                            example: 4cdf0ea4-159a-45aa-96f2-708e461130e1
                          server:
                            type: string
                            example: pc160234.csi.it
                      start_time:
                        type: string
                        example: 16-06-2017 14:58:50.352286
                      stop_time:
                        type: string
                        example: 16-06-2017 14:58:50.399747                            
                      args:
                        type: array
                      worker:
                        type: string
                        example: celery@tst-beehive-02
                      elapsed:
                        type: number
                        format: float
                        example: 0.0474607944
                      result:
                        type: boolean
                        example: true
                      ttl:
                        type: integer
                        example: 83582
                      type:
                        type: string
                        example: JOB
                      children:
                        type: array
                        items:
                          type: string
                          example: d069c405-d9db-45f3-967e-f052fbeb3c3e
        """  
        task_manager = controller.get_task_manager()
        res = task_manager.get_all_tasks(details=True)
        resp = {
            u'task-instances':res,
            u'count':len(res)
        }        
        return resp
    
class GetTasksCount(TaskApiView):
    def get(self, controller, data, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        resp = task_manager.count_all_tasks()
        return resp

'''
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
'''

class QueryTask(TaskApiView):
    def get(self, controller, data, oid, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        res = task_manager.query_task(oid)
        resp = {u'task-instance':res}
        return resp

'''
class QueryTaskStatus(TaskApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        res = task_manager.query_task_status(oid)
        resp = {u'task-instance-status':res}
        return resp'''
    
class GetTaskGraph(TaskApiView):
    def get(self, controller, data, oid, *args, **kwargs):    
        task_manager = controller.get_task_manager()
        res = task_manager.get_task_graph(oid)
        resp = {u'task-instance-graph':res}
        return resp    
    
class PurgeAllTasks(TaskApiView):
    def delete(self, controller, data, *args, **kwargs):
        task_manager = controller.get_task_manager()
        resp = task_manager.delete_task_instances()
        return (resp, 202)
    
class PurgeTasks(TaskApiView):
    def delete(self, controller, data, *args, **kwargs):
        task_manager = controller.get_task_manager()
        resp = task_manager.purge_tasks()
        return (resp, 202)  
    
class DeleteTask(TaskApiView):
    def delete(self, controller, data, oid, *args, **kwargs):
        task_manager = controller.get_task_manager()
        resp = task_manager.delete_task_instance(oid)
        return (resp, 202)  

'''
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
        return resp'''
    
class RunJobTest(TaskApiView):
    def post(self, controller, data, *args, **kwargs):    
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
            (u'worker/tasks', u'GET', GetAllTasks, {}),
            (u'worker/tasks/count', u'GET', GetTasksCount, {}),
            (u'worker/tasks/definitions', u'GET', GetTasksDefinition, {}),
            #(u'worker/tasks/active', u'GET', GetTasksActive, {}),
            #(u'worker/tasks/scheduled', u'GET', GetTasksScheduled, {}),
            #(u'worker/tasks/reserved', u'GET', GetTasksReserved, {}),
            #(u'worker/tasks/revoked', u'GET', GetTasksRevoked, {}),
            (u'worker/tasks/<oid>', u'GET', QueryTask, {}),
            #(u'worker/tasks/<oid>/status', u'GET', QueryTaskStatus, {}),
            (u'worker/tasks/<oid>/graph', u'GET', GetTaskGraph, {}),
            (u'worker/tasks', u'DELETE', PurgeAllTasks, {}),
            (u'worker/tasks/purge', u'DELETE', PurgeTasks, {}),
            (u'worker/tasks/<oid>', u'DELETE', DeleteTask, {}),
            #(u'worker/tasks/<oid>/revoke', u'DELETE', RevokeTask, {}),
            #(u'worker/tasks/time-limit', u'PUT', SetTaskTimeLimit, {}),
            (u'worker/tasks/test', u'POST', RunJobTest, {}),
        ]

        ApiView.register_api(module, rules)