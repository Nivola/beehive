'''
Created on Jan 25, 2017

@author: darkbk
'''
from kombu.pools import producers
from kombu import Connection, exceptions
from kombu import Exchange, Queue
from kombu.log import get_logger
from kombu.utils.debug import setup_logging
import time

logger = get_logger(__name__)

priority_to_routing_key = {'high': 'hipri',
                           'mid': 'midpri',
                           'low': 'lopri'}

connection = Connection('redis://10.102.160.240:6379/')
task_exchange = Exchange('events', type='direct')
task_queue = Queue('generic', task_exchange, routing_key='generic')
routing_key = 'generic'

def send_as_task(connection, fun, args=(), kwargs={}, priority='mid'):
    payload = {'fun': fun, 'args': args, 'kwargs': kwargs}
    routing_key = priority_to_routing_key[priority]

    with producers[connection].acquire(block=True) as producer:
        producer.publish(payload,
                         serializer='pickle',
                         compression='bzip2',
                         exchange=task_exchange,
                         declare=[task_exchange],
                         routing_key=routing_key)
        producer.release()
        
def send_event(id, type, creation, data, source, dest):
    
    payload = {'id':id, 'type':type, 'creation':creation, 
               'data':data, 'source':source, 'dest':dest}
    try:
        producer = producers[connection].acquire()
        producer.publish(payload,
                         serializer='json',
                         compression='bzip2',
                         exchange=task_exchange,
                         declare=[task_exchange],
                         routing_key=routing_key,
                         expiration=60)
    except exceptions.ConnectionLimitExceeded as ex:
        print ex
    

if __name__ == '__main__':
    #from kombu import Connection
    #from tasks import hello_task
    #connection = Connection('redis://10.102.160.240:6379/')
    #send_as_task(connection, fun=hello_task, args=('Kombu', ), kwargs={},
    #             priority='high')
    
    # setup root logger
    setup_logging(loglevel='DEBUG', loggers=[''])    
    
    send_event(1, 'booo', time.time(), 'data', 'source', 'dest')
    