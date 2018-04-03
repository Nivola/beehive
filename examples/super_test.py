import subprocess
from multiprocessing import Process
import os
from random import randint
from time import sleep


def subprocess_cmd(index):
    sleep(randint(0, 20))
    print 'process id: %s - index: %s' % (os.getpid(), index)
    res = subprocess.check_output([u'beehive', u'resource', u'tasks', u'test'], stderr=subprocess.STDOUT)
    print res


if __name__ == '__main__':
    print 'process id:', os.getpid()

    procs = []

    for index in xrange(100):
        proc = Process(target=subprocess_cmd, args=(index,))
        procs.append(proc)
        proc.start()

    for proc in procs:
        proc.join()
