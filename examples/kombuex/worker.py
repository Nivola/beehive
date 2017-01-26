'''
Created on Jan 25, 2017

@author: darkbk
'''
from kombu.mixins import ConsumerMixin
from kombu.log import get_logger
from kombu.utils import reprcall
from kombu import Exchange, Queue
#from kombu.utils import kwdict, reprcall

from queues import task_queues

logger = get_logger(__name__)

class Worker(ConsumerMixin):

    def __init__(self, connection):
        self.connection = connection
        self.exchange = Exchange('events', type='direct')
        self.queue = Queue('generic', self.exchange, routing_key='generic')
        
    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=self.queue,
                         accept=['pickle', 'json'],
                         callbacks=[self.process_task],
                         on_decode_error=self.decode_error)]

    def decode_error(self, message, exc):
        logger.error(exc)

    def process_task(self, body, message):
        print body
        '''fun = body['fun']
        args = body['args']
        kwargs = body['kwargs']
        logger.info('Got task: %s', reprcall(fun.__name__, args, kwargs))
        try:
            fun(*args, **kwargs)
            #fun(*args, **kwdict(kwargs))
        except Exception as exc:
            logger.error('task raised exception: %r', exc)'''
        message.ack()

if __name__ == '__main__':
    from kombu import Connection
    from kombu.utils.debug import setup_logging
    # setup root logger
    setup_logging(loglevel='DEBUG', loggers=[''])

    with Connection('redis://10.102.160.240:6379/') as conn:
        try:
            worker = Worker(conn)
            worker.run()
        except KeyboardInterrupt:
            print('bye bye')