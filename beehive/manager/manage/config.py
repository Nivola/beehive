'''
Created on Apr 28, 2014

@author: darkbk
'''

api_id = 'api'
api_name = 'cloudapi'

virtualenv_path = '/usr/local/lib/gibbon/cloudapi-01'

# database connection uri
db_uri = {'auth':'mysql+pymysql://auth:col98_e45+!@localhost:3306/auth',
          'apicore':'mysql+pymysql://apicore:col98_e45+!@localhost:3306/apicore',
          'resource':'mysql+pymysql://resource:col98_e45+!@localhost:3306/resource',
          'bpm':'',
          'platform':'mysql+pymysql://resource:col98_e45+!@localhost:3306/resource',
          'service':''}

db_uri = {'auth':'mysql+pymysql://auth:auth@localhost:3306/auth',
          'apicore':'mysql+pymysql://apicore:apicore@localhost:3306/apicore',
          'resource':'mysql+pymysql://cloudapi:cloudapi@10.102.160.240:3306/cloudapi',
          'bpm':'',
          'platform':'mysql+pymysql://cloudapi:cloudapi@localhost:3306/cloudapi',
          'monitor':'mysql+pymysql://monitor:monitor@localhost:3306/monitor',
          'service':''}

#
# cloudapi connection
#
proto = 'https'
#proto = 'http'
#host = '158.102.160.234'
#host = '172.16.0.16'
host = 'localhost'
#host = '10.102.47.208'
port = 6060
port = 1443
#port = 5000

#
# cloudapi event consumer
#
#event_host = '158.102.160.234'
#event_host = '172.16.0.16'
event_host = 'localhost'
event_port = 5500
event_server_port = 5501

redis_uri = 'localhost;6379;0'

task_broker_url = 'redis://localhost:6379/1'
task_result_backend = 'redis://localhost:6379/1'
scheduler_broker_url = 'redis://localhost:6379/2'
scheduler_result_backend = 'redis://localhost:6379/2'

#redis_uri = 'localhost;6379;0'
#host = '172.16.0.16'

#
# mail server
#
mail_server = 'mailfarm-app.csi.it'
mail_sender = 'sergio.tonani@csi.it'

#
# cloudapi service catalog
#
cloudapi_host = '10.102.160.12'
catalog1 = {u'name':u'cloudapi', 
            u'desc':u'cloudapi catalog internal',
            u'use':u'internal'}
catalog2 = {u'name':u'cloudapi', 
            u'desc':u'cloudapi catalog external',
            u'use':u'external'}

services1 = [{u'name':u'auth01',
              u'desc':'Authorization service 01', 
              u'type':'auth', 
              u'uri':'http://localhost:6060/api/auth/', 
              u'enabled':True},
             {u'name':u'catalog01',
              u'desc':'Catalog service 01', 
              u'type':'catalog', 
              u'uri':'http://localhost:6060/v1.0/catalog/',
              u'enabled':True},
             {u'name':u'config01',
              u'desc':'Configuration service 01', 
              u'type':'config', 
              u'uri':'http://localhost:6061/api/config/', 
              u'enabled':True},
             {u'name':u'admin01',
              u'desc':'Admin service 01', 
              u'type':'admin', 
              u'uri':'http://localhost:6061/api/admin/', 
              u'enabled':True},
             {u'name':u'event01',
              u'desc':'Event service 01', 
              u'type':'event', 
              u'uri':'http://localhost:6061/api/event/', 
              u'enabled':True},
             {u'name':u'resource01',
              u'desc':'Resource service 01', 
              u'type':'resource', 
              u'uri':'http://localhost:6062/api/res/', 
              u'enabled':True},
             {u'name':u'platform01',
              u'desc':'Platform service 01', 
              u'type':'platform', 
              u'uri':'http://localhost:6062/api/paltform/', 
              u'enabled':True},
             {u'name':u'resource-scheduler01',
              u'desc':'Resource scheduler service 01', 
              u'type':'scheduler', 
              u'uri':'http://localhost:6062/api/scheduler/', 
              u'enabled':True},
             {u'name':u'resource-task01',
              u'desc':'Resource task service 01', 
              u'type':'task', 
              u'uri':'http://localhost:6062/api/task/', 
              u'enabled':True},
             {u'name':u'service01',
              u'desc':'BusinessService service 01', 
              u'type':'service', 
              u'uri':'http://localhost:6063/api/service/', 
              u'enabled':True},
             {u'name':u'service-scheduler01',
              u'desc':'BusinessService scheduler service 01', 
              u'type':'scheduler', 
              u'uri':'http://localhost:6063/api/scheduler/', 
              u'enabled':True},
             {u'name':u'service-task01',
              u'desc':'BusinessService task service 01', 
              u'type':'task', 
              u'uri':'http://localhost:6063/api/task/', 
              u'enabled':True}]

services2 = [{u'name':u'auth02',
              u'desc':'Authorization service 02', 
              u'type':'auth', 
              u'uri':'http://%s:1443/api/auth/' % cloudapi_host, 
              u'enabled':True},
             {u'name':u'catalog02',
              u'desc':'Catalog service 02', 
              u'type':'catalog',
              u'uri':'http://%s:1443/v1.0/catalog/' % cloudapi_host, 
              u'enabled':True},
             {u'name':u'resource02',
              u'desc':'Resource service 02', 
              u'type':'resource', 
              u'uri':'http://%s:3443/api/res/' % cloudapi_host, 
              u'enabled':True},]              

endpoints = [{'name':'auth', 'host':host, 'port':[6060, 3030]},
             {'name':'config', 'host':host, 'port':[6061, 3031]},
             {'name':'event', 'host':host, 'port':[6061, 3031]},
             {'name':'scheduler', 'host':host, 'port':[6061, 3031]},
             {'name':'admin', 'host':host, 'port':[6061, 3031]},             
             {'name':'resource', 'host':host, 'port':[6062, 3032]},
             {'name':'platform', 'host':host, 'port':[6062, 3032]},
             {'name':'bpm', 'host':host, 'port':[6063, 3033]},
             {'name':'service', 'host':host, 'port':[6064, 3034]},
             {'name':'monitor', 'host':host, 'port':[6065, 3035]},
             ]

#
# cloudapi gateways
#
gateways = [{"name":"internet_spice", "host":"84.240.187.251", "port":80, "type":"spice"},
            {"name":"internet_vnc", "host":"84.240.187.251", "port":80, "type":"vnc"},
            {"name":"rupar_spice", "host":"10.102.81.197", "port":15900, "type":"spice"},
            {"name":"rupar_vnc", "host":"10.102.81.197", "port":15900, "type":"vnc"},]

#
# cloudapi identity providers
#
auths = [{'type':'db', 'host':'localhost', 'domain':'local', 'ssl':False, 'timeout':30},
         {'type':'ldap', 'host':'dr-csidc07.domnt.csi.it', 'domain':'domnt.csi.it', 'ssl':True, 'timeout':30},
         {'type':'ldap', 'host':'10.102.90.200', 'domain':'clskdom.lab', 'ssl':False, 'timeout':30},
         {'type':'ldap', 'host':'ad.regione.piemonte.it', 'domain':'regione.piemonte.it', 'ssl':False, 'timeout':30},
         {'type':'ldap', 'host':'ad.provincia.torino.it', 'domain':'provincia.torino.it', 'ssl':False, 'timeout':30},
         {'type':'ldap', 'host':'ad.comune.torino.it', 'domain':'comune.torino.it', 'ssl':False, 'timeout':30},]

queues = [{'name':'queue.event', 'queue':'cloudapi.event', 'uri':redis_uri},
          {'name':'queue.process', 'queue':'cloudapi.process.event', 'uri':redis_uri},
          {'name':'queue.monitor', 'queue':'cloudapi.monitor', 'uri':redis_uri},]

#
# cloudapi internal user
#
api_user = {'name':'DEJD983UDM8CH7CH437CHN73@local', 'pwd':'MC4UR84FC4HCFH47NCMF74NF7'}

authuser = ('admin@local', 'localhost', None)

# first container
'''
conn = {
    'api':('http://172.16.0.19:8080/client/api',
           'OkeTG2ntyuim408elcgNzOxA5xUUky67zJDbq7sfB_gdKEtMihu_YVohmgetfVgCGQFq13rT0dJmNeFHuJWAFw',
           '4HVJYDkcRBjBoyXHy4GJTxF7NBWDFWNpsS7f82o-UdVwBehxPiNAqdCcv7e1slpqJ4uvNowhdoeTqOYHfowqLA',
           5),
    'db':('172.16.0.19', '3406', 'cloud', 'cloud', 'testlab', 5),
    'zone':'zona_kvm_01'}
'''
'''
conn = {
    'api':('http://10.102.90.209:8080/client/api',
           'OkeTG2ntyuim408elcgNzOxA5xUUky67zJDbq7sfB_gdKEtMihu_YVohmgetfVgCGQFq13rT0dJmNeFHuJWAFw',
           '4HVJYDkcRBjBoyXHy4GJTxF7NBWDFWNpsS7f82o-UdVwBehxPiNAqdCcv7e1slpqJ4uvNowhdoeTqOYHfowqLA',
          5),
    'db':('10.102.90.209', '3306', 'cloud', 'cloud', 'testlab', 5),
    'zone':'zona_kvm_01'}
{'class':'gibboncloudapi.module.resource.plugins.cloudstack.CloudstackContainer',
               'name':'clsk442-1',
               'desc':'Cloudstack 4.4.2 instance 1',
               'conn':{'api':('http://172.25.5.4:8080/client//api',
                              'CdHcMAmIWtnxEcTI5WTl337V9Z1Q_4gSDEIb0Hh5wWVVMUJEHlf0Xbt5-CGbv7sMCA9bYoN70lqgfGgjn-Ffjg',
                              'Wn4Pk5MeAZZLlDkqF3e-Nm1CR1TE_yUz1KyZHSKToLX6a7hJo9KyBnQdjoj5anKcObLJbDi0b1cgPnkXhvbfTQ',
                              5),
                       'db':('172.25.5.4', '3306', 'cloud', 'cloud', 'cs1$topix', 5),
                       'zone':'z1c442'}},
'''
'''
containers = [{'class':'gibboncloudapi.module.resource.plugins.cloudstack.CloudstackContainer',
               'name':'clsk442-test',
               'desc':'Cloudstack 4.4.2 test',
               'conn':{'api':('http://10.102.90.209:8080/client/api',
                       'OkeTG2ntyuim408elcgNzOxA5xUUky67zJDbq7sfB_gdKEtMihu_YVohmgetfVgCGQFq13rT0dJmNeFHuJWAFw',
                       '4HVJYDkcRBjBoyXHy4GJTxF7NBWDFWNpsS7f82o-UdVwBehxPiNAqdCcv7e1slpqJ4uvNowhdoeTqOYHfowqLA',
                        5),
                       'db':('10.102.90.209', '3306', 'cloud', 'cloud', 'testlab', 5),
                       'zone':'zona_kvm_01'}},
              {'class':'gibboncloudapi.module.resource.plugins.cloudstack.CloudstackContainer',
               'name':'clsk442-prod1',
               'desc':'Cloudstack 4.4.2 prod 1',
               'conn':{'api':('http://clsk-mgmt01.csi.it:8080/client/api',
                       'tMY0xYpg5A5FJRTOs8jUfYx_ErHeglRl90ST5ljwAFWaMtFuavRQdaqPBXax2HcH6WsYCEqLZdh0Q7w4TmaLOw',
                       'WK5sJy3e8ZTrrhgQfOxGXot_fsGmbyraYP5tv3gRh4X-woHnyrdZc561DXqoNP70r14tjSHZdXGWRoJbVZGpMA',
                        5),
                       'db':('', '3306', '', '', '', 5),
                       'zone':'zone_kvm_01'}},
              {'class':'gibboncloudapi.module.resource.plugins.cloudstack.CloudstackContainer',
               'name':'clsk442-prod2',
               'desc':'Cloudstack 4.4.2 prod 2',
               'conn':{'api':('http://clsk-mgmt02.csi.it:8080/client/api',
                       'GEMWsQbnZdgZlENC0jXQrQfeKwT_ppccd6f03rbSEgYHNb0VLwicymk2xtsw4BTMzxWx9nGHFthconY00LUMzg',
                       'GJbo9WmDZMTEoboAuwXHpODH0CvfQQOACnQiuwQVzv1cIkKSVqsWClbM_eBsadfxEjS8QeLcGmCItCFi0bm-Wg',
                        5),
                       'db':('', '3306', '', '', '', 5),
                       'zone':'zona_kvm01'}},
              {'class':'gibboncloudapi.module.resource.plugins.openstack.OpenstackContainer',
               'name':'ostack-1',
               'desc':'Openstack kilo instance 1',
               'conn':{'auth_url':'http://172.25.5.60:5000/v3',
                        'user_domain_name': 'default',
                        'project_domain_name': 'default',    
                        'project_name': 'admin',
                        'username': 'admin',
                        'password': 'Opstkcs1'}},
              {'class':'gibboncloudapi.module.resource.plugins.vsphere.VsphereContainer',
               'name':'vcenter-1',
               'desc':'vsphere vcenter 1',
               'conn':{'api':({'host':'vc-tstvcloud.vfarm.csi.it',
                                'user':'administrator@vsphere.local',
                                'pwd':'Admin$01',
                                'port':'443'}, 5),
                        'db':()}},             
              ]
'''