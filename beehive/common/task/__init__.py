from celery import Task
from celery.utils.log import get_task_logger
import ujson as json
from beecell.simple import truncate

logger = get_task_logger(__name__)

class BaseTask(Task):
    abstract = True
    inner_type = 'TASK'
    prefix = 'celery-task-shared-'
    prefix_stack = 'celery-task-stack-'
    expire = 3600
    
    def __init__(self, *args, **kwargs):
        Task.__init__(self, *args, **kwargs)
        #task_short_name = {u'task_name':self.name.split(u'.')[-1]}
        #logger = logging.LoggerAdapter(get_task_logger(__name__), task_short_name)
        self.logger = logger
        
        try:
            self._redis = self.app.api_manager.redis_taskmanager.conn
        except:
            self._redis = None
    
    '''
    def __call__(self, *args, **kwargs):
        """In celery task this function call the run method, here you can
        set some environment variable before the run of the task"""
        res = self.run(*args, **kwargs)
        return res'''

    #
    # shared area
    #
    def get_shared_data(self, task_id):
        """Get data from shared memory area. Use this to pass data from different
        tasks. Shared area could not ensure synchronization
        """
        data = None
        val = self._redis.get(self.prefix + task_id)
        if val is not None:
            data = json.loads(val)
        else:
            data = {} 
        return data
    
    def set_shared_data(self, task_id, data):
        """Set data to shared memory area. Use this to pass data from different
        tasks. Shared area could not ensure synchronization
        """
        val = json.dumps(data)
        self._redis.setex(self.prefix + task_id, self.expire, val)
        #logger.debug(u'Set shared data for job %s: %s' % 
        #             (task_id, truncate(data)))
        return True
    
    def remove_shared_area(self, task_id):
        """Remove shared memory area reference from redis"""
        keys = self._redis.keys(self.prefix + task_id)
        res = self._redis.delete(*keys)
        return res

    #
    # shared stack area
    #
    def pop_stack_data(self, task_id):
        """Pop item from shared memory stack. Use this to pass data from different
        tasks that must ensure synchronization.
        """
        data = None
        val = self._redis.lpop(self.prefix_stack + task_id)
        if val is not None:
            data = json.loads(val)
        logger.debug('Pop stack data for job %s: %s' % 
                     (task_id, truncate(data)))   
        return data
    
    def push_stack_data(self, task_id, data):
        """Set data to shared memory stack. Use this to pass data from different
        tasks that must ensure synchronization.
        """
        val = json.dumps(data)
        self._redis.lpush(self.prefix_stack + task_id, val)
        logger.debug('Push stack data for job %s: %s' % 
                     (task_id, truncate(data)))
        return True
    
    def remove_stack(self, task_id):
        """Remove shared memory stack reference from redis"""
        try:
            keys = self._redis.keys(self.prefix_stack + task_id)
            res = self._redis.delete(*keys)
            return res
        except:
            pass

    def after_return(self, *args, **kwargs):
        """Handler called after the task returns.
        
        Parameters:    
    
            status - Current task state.
            retval - Task return value/exception.
            task_id - Unique id of the task.
            args - Original arguments for the task that returned.
            kwargs - Original keyword arguments for the task that returned.
            einfo - ExceptionInfo instance, containing the traceback (if any).
    
        The return value of this handler is ignored.
        """
        super(BaseTask, self).after_return(*args, **kwargs) 

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """This is run by the worker when the task fails.
        
        Parameters:    
    
            exc - The exception raised by the task.
            task_id - Unique id of the failed task.
            args - Original arguments for the task that failed.
            kwargs - Original keyword arguments for the task that failed.
            einfo - ExceptionInfo instance, containing the traceback.
    
        The return value of this handler is ignored.
        """
        pass