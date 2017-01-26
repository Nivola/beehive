'''
Created on Jun 17, 2016

@author: darkbk
'''
from celery import Celery


def my_monitor(app):
    state = app.events.State()

    def announce_failed_tasks(event):
        state.event(event)
        # task name is sent only with -received event, and state
        # will keep track of this for us.
        task = state.tasks.get(event['uuid'])

        print('TASK FAILED: %s[%s] %s' % (
            task.name, task.uuid, task.info(), ))
        
    def announce_successes_tasks(event):
        state.event(event)
        # task name is sent only with -received event, and state
        # will keep track of this for us.
        task = state.tasks.get(event['uuid'])

        print('TASK SUCCESS: %s[%s] %s' % (
            task.name, task.uuid, task.info(), ))
        print task.__dict__
        
    def announce_received_tasks(event):
        state.event(event)
        # task name is sent only with -received event, and state
        # will keep track of this for us.
        task = state.tasks.get(event['uuid'])

        print('TASK RECEIVED: %s[%s] %s' % (
            task.name, task.uuid, task.info(), ))
        print task.__dict__        

    with app.connection() as connection:
        recv = app.events.Receiver(connection, handlers={
                'task-failed': announce_failed_tasks,
                'task-succeeded': announce_successes_tasks,
                'task-received': announce_received_tasks,
                #'*': state.event,
        })
        recv.capture(limit=None, timeout=None, wakeup=True)

if __name__ == '__main__':
    print 'Start monitor'
    app = Celery(broker='redis://10.102.160.12:6379/1')
    my_monitor(app)