#!/usr/bin/env python

'''
Created on Apr 12, 2017

@author: darkbk
'''
import os, sys
import getopt
import json

VERSION = u'0.1.0'

from beehive.common.apiclient import BeehiveApiClient

inventory = {
    "account1"   : {
        "hosts"   : [ "10.102.185.50", "10.102.185.115" ],
        "vars"    : {
            "a"   : True
        }
    },
    "sg-zone01-default"  : [ "10.102.185.50", "10.102.185.115" ],
    "vpc-zone01-default"     : {
        "hosts"   : [ "10.102.185.50", "10.102.185.115" ],
        "vars"    : {
            "b"   : True
        },
        "children": [ "marietta", "5points" ]
    },
}

hosts = {
    "10.102.184.50":{
        "favcolor"   : "red",
        "ntpserver"  : "wolf.example.com",
        "monitoring" : "pack.example.com"
    }
}

config = {
    "endpoint":["http://10.102.184.52:6060"],
    "user":"admin@local",
    "pwd":"testlab",
    "catalog":3,
    "provider":13,
    "super-zone":2992
}

client = BeehiveApiClient(config[u'endpoint'], 
                          config[u'user'], 
                          config[u'pwd'],
                          config[u'catalog'])

uri = u'/v1.0/providers/%s/instances/' % config[u'provider']
data = u'super-zone=%s' % (config[u'super-zone'])
instances = client.invoke(u'resource', uri, u'GET', data=data, parse=True)[u'instances']
inventory = {}
for instance in instances:
    ip = instance[u'networks'][0][u'ip']
    if ip is not None:
        try:
            inventory[instance[u'parent_name']][u'hosts'].append(ip)
        except:
            inventory[instance[u'parent_name']] = {u'hosts':[ip]}

def main(run_path, argv):
    """Beehive ansible dynamic inventory
    """
    try:
        opts, args = getopt.getopt(argv, u'l:hv',
                                   [u'help', u'list', u'host', u'version'])
    except getopt.GetoptError:
        print(main.__doc__)
        return 2
    for opt, arg in opts:
        if opt in (u'-h', u'--help'):
            print(main.__doc__)
            return 0
        elif opt in (u'-v', u'--version'):
            print 'auth %s' % VERSION
            return 0
        elif opt in (u'--list'):
            print json.dumps(inventory, indent=2)
            return 0
        elif opt in (u'--host'):
            try:
                host = args.pop()
                print json.dumps(hosts[host], indent=2)
                return 0
            except:
                return 1
        
if __name__ == u'__main__':    
    run_path = os.path.dirname(os.path.realpath(__file__))
    retcode = main(run_path, sys.argv[1:])
    sys.exit(retcode)