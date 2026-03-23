# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte


from kombu.pools import producers
from kombu import Exchange, Queue
from kombu import Connection, Producer
from datetime import datetime

print("INIZIO")
# external port. See kubectl services
connection = Connection('amqp://beehive:<password>@cmpvc1-node01.site03.nivolapiemonte.it:30679/nivola')

# pool = connection.ChannelPool(2)
# c1 = pool.acquire()
# c1.release()

with producers[connection].acquire(block=True) as producer:
    now = datetime.now() # current date and time
    date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
    msg = {"test": date_time}
    print(f"msg: {msg}")

    broker_exchange = 'celery.resource.podvc1'
    task_exchange = Exchange(broker_exchange, type='direct')
    print("Exchange")

    queue_name = "%s.queue" % broker_exchange
    routing_key = "%s.key" % broker_exchange

    producer.publish(
        msg,
        serializer="json",
        compression="bzip2",
        exchange=task_exchange,
        declare=[task_exchange],
        routing_key=routing_key,
        # expiration=60,
        # delivery_mode=1
        # see https://docs.celeryq.dev/projects/kombu/en/v5.3.5/userguide/producers.html
        retry=True,
        # parameters supported by the retry_over_time() function
        retry_policy={
            "interval_start": 0, # First retry immediately,
            "interval_step": 2,  # then increase by 2s for every retry.
            "interval_max": 30,  # but don't exceed 30s between retries.
            "max_retries": 32,   # give up after 30 tries.
            # "timeout": 29,
        },
        timeout=29,
    )

print("FINE")
