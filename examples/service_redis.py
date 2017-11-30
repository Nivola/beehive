'''
Created on Nov 30, 2017

@author: io
'''
import redis
import json
import amqp
from kombu.transport.pyamqp import Channel
from kombu import Connection, exceptions
from kombu.pools import producers
from kombu import Exchange, Queue
import base64

'''
client = redis.StrictRedis(host=u'10.102.184.65', port=6379, db=0)

body = {u'msg':u'ciao'}
message = amqp.Message(body, content_type=u'application/json')
print message
res = client.lpush(u'beehive.service.queue', message)
print res'''

'''
body = {u'msg':u'ciao'}
exchange = Exchange(u'beehive.service', type=u'direct',
                    delivery_mode=1, durable=False)
routing_key = u'beehive.service.key'
redis_uri = u'redis://10.102.184.65:6379/0'
conn = Connection(redis_uri)
with producers[conn].acquire() as producer:
    msg = body
    res = producer.publish(msg,
                     serializer=u'json',
                     compression=None,
                     exchange=exchange,
                     routing_key=routing_key,
                     declare=[exchange],
                     expiration=60,
                     delivery_mode=1)
    print res'''


#print base64.decodestring("eyJtc2ciOiAiY2lhbyJ9")

#body = "eyJtc2ciOiAiY2lhbyJ9"
body = {u'msg':u'ciao'}
client = redis.StrictRedis(host=u'10.102.184.65', port=6379, db=0)


################# redis kombu
body = base64.encodestring(json.dumps(body))
message = {"body": body,
           "headers": {}, 
           "content-type": "application/json", 
           "properties": {
               "priority": 0, 
               "body_encoding": "base64", 
               "expiration": "60000", 
               "delivery_info": {
                   "routing_key": "beehive.service.key", 
                   "exchange": "beehive.service"}, 
                "delivery_mode": 1, 
                "delivery_tag": "c353f7f9-03e6-4376-8fa7-2e19f0763e56"
            }, 
           "content-encoding": "utf-8"
           }

res = client.lpush(u'beehive.service.queue', json.dumps(message))
print res

################### redis semple
message = json.dumps(body)
res = client.publish(u'beehive.service', message)
print res


