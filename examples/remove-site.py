import subprocess
import json
import time

def cmd(command):
    """Run a shell command as an external process and return response or error.
    
    :param command: list like ['ls', '-l']
    """
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode == 0:
        return out
    else:
        return err

data = cmd(['./manage.py', '-f', 'json', '-e', 'test', '-o', '0', 'provider', '13', 'sites', 'list', 'name=siteTO'])
data = json.loads(data).get(u'sites')
for item in data:
    print('------------- Site ---------------')
    oid = str(item.get(u'id'))
    uuid = item.get(u'uuid')
    name = item.get(u'name')
    print(item.get(u'id'), item.get(u'uuid'), item.get(u'name'))
    cmd(['./manage.py', '-f', 'json', '-e', 'test', '-o', '0', 'provider', '13', 'sites', 'delete', oid])
    print('------------- Linked ---------------')
    data1 = cmd(['./manage.py', '-f', 'json', '-e', 'test', '-o', '0', 'resource', 'resources', 'tree', oid])
    data1 = json.loads(data1).get(u'resource-tree')
    for item1 in data1['children']:
        oid1 = str(item1.get(u'id'))
        uuid1 = item1.get(u'uuid')
        name1 = item1.get(u'name')
        def1 = item1.get(u'definition')
        print(oid1, uuid1, name1, def1)
    print('------------- Not Linked ---------------')
    data1 = cmd(['./manage.py', '-f', 'json', '-e', 'test', '-o', '0', 'resource', 'resources', 'list', 'name='+uuid+'-%'])
    data1 = json.loads(data1).get(u'resources')
    for item1 in data1:
        oid1 = str(item1.get(u'id'))
        uuid1 = item1.get(u'uuid')
        name1 = item1.get(u'name')
        def1 = item1.get(u'definition')
        print(oid1, uuid1, name1, def1)
        if def1 == 'Openstack.Domain.Project':
            cmd(['./manage.py', '-f', 'json', '-e', 'test', '-o', '0', 'openstack', '22', 'projects', 'delete', oid1])
        elif def1 == 'Vsphere.DataCenter.Folder':
            cmd(['./manage.py', '-f', 'json', '-e', 'test', '-o', '0', 'vpshere', '16', 'folders', 'delete', oid1])

    time.sleep(3)

'''
import sh

manage = sh.command(u'./manage.py')
data = manage('-f', 'json', '-e', 'test', 'provider', '13', 'sites', 'list')'''
