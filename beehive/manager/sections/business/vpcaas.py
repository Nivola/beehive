"""
Created on Nov 20, 2017

@author: darkbk
"""
import logging
import urllib
import json

from cement.core.controller import expose

from beehive.manager.sections.platform import AnsibleController
from beehive.manager.util.ansible2 import Runner
from beehive.manager.util.controller import BaseController, ApiController, check_error
from re import match
from beecell.simple import truncate, id_gen, getkey
from urllib import urlencode
from beehive.manager.sections.business import SpecializedServiceControllerChild
from beecell.paramiko_shell.shell import ParamikoShell

logger = logging.getLogger(__name__)


class VPCaaServiceController(AnsibleController):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'

    class Meta:
        label = 'vpcaas'
        stacked_on = 'business'
        stacked_type = 'nested'
        description = "Virtual Private Cloud Service management"
 
    def _setup(self, base_app):
        BaseController._setup(self, base_app)

    @expose(aliases=[u'get <account>'], aliases_only=True)
    @check_error
    def info(self):
        """Get compute service info
        """
        data_search = {u'owner-id': self.get_arg(name=u'account')}
        uri = u'%s/computeservices' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data_search)) \
            .get(u'DescribeComputeResponse') \
            .get(u'computeSet')[0]
        self.result(res, details=True, maxsize=40)


class VPCaaServiceControllerChild(SpecializedServiceControllerChild):
    baseuri = u'/v1.0/nws'
    subsystem = u'service'
 
    class Meta:
        stacked_on = 'vpcaas'
        stacked_type = 'nested'


class ImageServiceController(VPCaaServiceControllerChild):
    class Meta:
        label = 'images'
        description = "Images service management"

    @expose(aliases=[u'list [field=..]'], aliases_only=True)
    @check_error
    def list(self):
        """List all virtual machine
    - field: account, ids, size
        - accounts: list of account id comma separated
        - ids: list of image id
        - size: number of records
        """
        data_search = {}
        data_search[u'owner-id.N'] = self.split_arg(u'accounts')
        data_search[u'image-id.N'] = self.split_arg(u'ids')
        data_search[u'Nvl-MaxResults'] = self.get_arg(name=u'size', default=10, keyvalue=True)
        data_search[u'Nvl-NextToken'] = self.get_arg(name=u'page', default=0, keyvalue=True)

        uri = u'%s/computeservices/image/describeimages' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data_search, doseq=True))
        res = res.get(u'DescribeImagesResponse')
        page = data_search[u'Nvl-NextToken']
        resp = {
            u'count': len(res.get(u'imagesSet')),
            u'page': page,
            u'total': res.get(u'nvl-imageTotal'),
            u'sort': {u'field': u'id', u'order': u'asc'},
            u'instances': res.get(u'imagesSet')
        }

        headers = [u'id', u'name', u'state', u'type', u'account', u'platform']
        fields = [u'imageId', u'name', u'imageState', u'imageType', u'imageOwnerAlias', u'platform']
        self.result(resp, key=u'instances', headers=headers, fields=fields, maxsize=40)

    @expose(aliases=[u'add <name> <account> <type>'], aliases_only=True)
    @check_error
    def add(self):
        """Create an image
        """
        data = {
            u'ImageName': self.get_arg(name=u'name'),
            u'owner_id': self.get_arg(name=u'account'),
            u'ImageType': self.get_arg(name=u'type')
        }
        uri = u'%s/computeservices/image/createimage' % self.baseuri
        res = self._call(uri, u'POST', data={u'image': data}, timeout=600)
        logger.info(u'Add image: %s' % truncate(res))
        res = res.get(u'CreateImageResponse').get(u'imageSet')[0].get(u'imageId')
        res = {u'msg': u'Add image %s' % res}
        self.result(res, headers=[u'msg'])


class VMServiceController(VPCaaServiceControllerChild):
    class Meta:
        label = 'vms'
        description = "Virtual Machine service management"

    @expose(aliases=[u'list [field=..]'], aliases_only=True)
    @check_error
    def list(self):
        """List all virtual machine
    - field: account, ids, size
        - accounts: list of account id comma separated
        - ids: list of instance id
        - size: number of records
        """
        data_search = {}
        data_search[u'owner-id.N'] = self.split_arg(u'accounts')
        data_search[u'instance-id.N'] = self.split_arg(u'ids')
        data_search[u'MaxResults'] = self.get_arg(name=u'size', default=10, keyvalue=True)
        data_search[u'NextToken'] = self.get_arg(name=u'page', default=0, keyvalue=True)

        uri = u'%s/computeservices/instance/describeinstances' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data_search, doseq=True))
        res = res.get(u'DescribeInstancesResponse')
        page = res.get(u'nextToken')
        res = res.get(u'reservationSet')[0]
        resp = {
            u'count': len(res.get(u'instancesSet')),
            u'page': page,
            u'total': res.get(u'nvl-instanceTotal'),
            u'sort': {u'field': u'id', u'order': u'asc'},
            u'instances': res.get(u'instancesSet')
        }

        headers = [u'id', u'name', u'type', u'state', u'launchTime', u'account', u'availabilityZone',
                   u'privateIp', u'image', u'subnet']
        fields = [u'instanceId', u'name', u'instanceType', u'instanceState.name', u'launchTime',
                  u'OwnerAlias', u'placement.availabilityZone', u'privateIpAddress', u'imageName',
                  u'subnetName']

        def color_error(val):
            if val == u'error':
                val = self.app.colored_text.output(val, u'REDonBLACK')
            return val

        transform = {u'state': color_error}
        self.result(resp, key=u'instances', headers=headers, fields=fields, transform=transform, maxsize=40)

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get virtual machine
        """
        data_search = {u'instance-id.N': [self.get_arg(u'id')]}
        uri = u'%s/computeservices/instance/describeinstances' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data_search, doseq=True)) \
            .get(u'DescribeInstancesResponse') \
            .get(u'reservationSet')[0].get(u'instancesSet')[0]
        self.result(res, details=True, maxsize=40)

    @expose(aliases=[u'add name=.. account=.. type=.. subnet=.. image=.. security-group=.. [sshkey=..] [pwd=..] '
                     u'[disks=..]'],
            aliases_only=True)
    @check_error
    def add(self):
        """Create a virtual machine
    - sshkey: use this optional parameter to set sshkey. Pass reference to a file
    - pwd: vm password [default=mypass]
    - disks: list of additional disk sizes comma separated. Ex. 5,10
        """
        name = self.get_arg(name=u'name', keyvalue=True, required=True)
        account = self.get_account(self.get_arg(name=u'account', keyvalue=True, required=True))
        itype = self.get_service_def(self.get_arg(name=u'type', keyvalue=True, required=True))
        subnet = self.get_service_instance(self.get_arg(name=u'subnet', keyvalue=True, required=True),
                                           account_id=account)
        image = self.get_service_instance(self.get_arg(name=u'image', keyvalue=True, required=True), account_id=account)
        sg = self.get_service_instance(self.get_arg(name=u'security-group', keyvalue=True, required=True),
                                       account_id=account)
        sshkey = self.get_arg(name=u'sshkey', default=None, keyvalue=True, required=False)
        pwd = self.get_arg(name=u'pwd', default=u'mypass', keyvalue=True, required=False)
        disks = self.get_arg(name=u'disks', default=None, keyvalue=True, required=False)

        data = {
            u'Name': name,
            u'owner_id': account,
            u'AdditionalInfo': u'',
            u'SubnetId': subnet,
            u'InstanceType': itype,
            u'AdminPassword': pwd,
            u'ImageId': image,
            u'SecurityGroupId_N': [sg],
        }
        if disks is not None:
            blocks = []
            for disk in disks.split(u','):
                blocks.append({u'Ebs': {u'VolumeSize': disk}})
            data[u'BlockDeviceMapping_N'] = blocks

        if sshkey is not None:
            key = self.load_file(sshkey)
            key = key.replace(u'\n', u'')
            data[u'KeyValue'] = key

        uri = u'%s/computeservices/instance/runinstances' % self.baseuri
        res = self._call(uri, u'POST', data={u'instance': data}, timeout=600)
        logger.info(u'Add virtual machine instance: %s' % truncate(res))
        res = res.get(u'RunInstanceResponse').get(u'instancesSet')[0].get(u'instanceId')
        res = {u'msg': u'Add virtual machine %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'start [field=<id1, id2>] '], aliases_only=True)
    @check_error
    def start(self):
        """Start service instance by field
    - field: owner-id.N, instance-id.N
        """
        data_search = {}
        data_search[u'owner-id.N'] = self.split_arg(u'owner-id.N')
        data_search[u'instance-id.N'] = self.split_arg(u'instance-id.N')

        uri = u'%s/computeservices/instance/startinstances' % self.baseuri
        res = self._call(uri, u'GET', data=urlencode(data_search, doseq=True)).get(u'StartInstancesResponse')\
            .get(u'instancesSet', [])
        headers = [u'id', u'name', u'state',  u'currentState', u'previousState']
        fields = [u'id', u'name', u'state',  u'currentState', u'previousState']
        self.result(res, headers=headers, fields=fields, maxsize=40)

    @expose(aliases=[u'stop [field=<id1, id2>] force=true|false '], aliases_only=True)
    @check_error
    def stop(self):
        """Stop service instance by field
    - field: list of owner-id.N, instance-id.N
    - field: force is set to true forces the instances to stop (default is false)
        """
        data_search = {}
        data_search[u'instance-id.N'] = self.split_arg(u'instance-id.N')
        data_search[u'Force'] = self.get_arg(default=False, name=u'Force', keyvalue=True)

        uri = u'%s/computeservices/instance/stopinstances' % self.baseuri
        res = self._call(uri, u'GET', data=urlencode(data_search, doseq=True)).get(u'StopInstancesResponse')\
            .get(u'instancesSet', [])
        headers = [u'id', u'name', u'state',  u'currentState', u'previousState']
        fields = [u'id', u'name', u'state',  u'currentState', u'previousState']
        self.result(res, headers=headers, fields=fields, maxsize=40)

    @expose(aliases=[u'delete <id>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete service instance
    - field: can be recursive
        """
        value = self.get_arg(name=u'id')
        data = {
            u'InstanceId_N': [value]
        }
        uri = u'%s/computeservices/instance/terminateinstances' % self.baseuri
        res = self._call(uri, u'DELETE', data=data, timeout=600)
        logger.info(res)
        res = {u'msg': u'Delete virtual machine %s' % value}
        self.result(res, headers=[u'msg'], maxsize=200)

    @expose()
    @check_error
    def types(self):
        """List virtual machine types
        """
        data = urllib.urlencode({u'plugintype': u'ComputeInstance'})
        uri = u'%s/srvcatalogs/all/defs' % self.baseuri
        res = self._call(uri, u'GET', data=data)
        logger.info(res)
        headers = [u'id', u'uuid', u'instance_type', u'version', u'status', u'active', u'creation']
        fields = [u'id', u'uuid', u'name', u'version', u'status', u'active', u'date.creation']
        self.result(res, key=u'servicedefs', headers=headers, fields=fields)

    @expose(aliases=[u'ssh <id> <user> [sshkey=..]'], aliases_only=True)
    @check_error
    def ssh(self):
        """Opens ssh connection over provider instance
        """
        oid = self.get_arg(name=u'id')
        user = self.get_arg(name=u'user')
        sshkey = self.get_arg(name=u'sshkey', default=None, keyvalue=True)
        data_search = {u'instance-id.N': [oid]}
        uri = u'%s/computeservices/instance/describeinstances' % self.baseuri
        server = self._call(uri, u'GET', data=urllib.urlencode(data_search, doseq=True)) \
            .get(u'DescribeInstancesResponse') \
            .get(u'reservationSet')[0].get(u'instancesSet')[0]
        fixed_ip = getkey(server, u'privateIpAddress')

        client = ParamikoShell(fixed_ip, user, keyfile=sshkey)
        client.run()

    @expose(aliases=[u'ansible [ssh-key=..]'], aliases_only=True)
    @check_error
    def ansible(self):
        """Execute command on managed platform nodes
    - group: ansible group
    - cmd: shell command
        """
        ssh_key = self.get_arg(name=u'ssh-key', default=u'%s/../configs/test/.ssh/vm.id_rsa' % self.ansible_path,
                               keyvalue=True)
        user = self.get_arg(name=u'ssh-user', default=u'centos', keyvalue=True)

        data_search = {}
        data_search[u'MaxResults'] = 100
        data_search[u'NextToken'] = 0

        uri = u'%s/computeservices/instance/describeinstances' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data_search, doseq=True))
        res = res.get(u'DescribeInstancesResponse')

        inventory_dict = {
            u'all': {
                u'vars': {
                    u'ansible_user': user,
                    u'ansible_ssh_private_key_file': ssh_key,
                }
            }
        }
        for item in res.get(u'reservationSet', [])[0].get(u'instancesSet'):
            account = item.get(u'OwnerAlias', None)
            host = item.get(u'privateIpAddress', None)
            if account is not None and host is not None:
                try:
                    inventory_dict[account][u'hosts'].append(host)
                except:
                    inventory_dict[account] = {u'hosts': [host]}
        path_lib = u'%s/library/beehive/' % self.ansible_path
        runner = Runner(inventory=inventory_dict, verbosity=self.verbosity, module=path_lib, vault_password=self.vault)
        res = runner.get_inventory()
        logger.debug(u'Ansible inventory nodes: %s' % res)

        # cache inventory dict
        self.cache_data_on_disk(u'ansible', inventory_dict)

        resp = []
        for k, v in res.items():
            resp.append({u'group': k, u'hosts': v})
        resp = sorted(resp, key=lambda x: x.get(u'group'))

        for i in resp:
            print(u'%30s : %s' % (i[u'group'], u', '.join(i[u'hosts'][:6])))
            for n in range(1, len(i[u'hosts']) / 6):
                print(u'%30s : %s' % (u'', u', '.join(i[u'hosts'][n * 6:(n + 1) * 6])))

    def __cmd(self, group, cmd):
        """Execute command on group of virtual machines
    - group: virtual machines group
    - cmd: shell command
        """
        # read cached inventory dict
        inventory_dict = self.read_cache_from_disk(u'ansible')
        path_lib = u'%s/library/beehive/' % self.ansible_path
        runner = Runner(inventory=inventory_dict, verbosity=self.verbosity, module=path_lib, vault_password=self.vault)
        tasks = [
            dict(action=dict(module=u'shell', args=cmd), register=u'shell_out'),
        ]
        runner.run_task(group, tasks=tasks, frmt=u'text')

    def __playbook(self, group, run_data, playbook=None):
        """Execute a playbook on group of virtual machines
    - group: virtual machines group
    - cmd: shell command
        """
        # read cached inventory dict
        inventory_dict = self.read_cache_from_disk(u'ansible')
        path_lib = u'%s/library/beehive/' % self.ansible_path
        runner = Runner(inventory=inventory_dict, verbosity=self.verbosity, module=path_lib, vault_password=self.vault)
        tags = run_data.pop(u'tags')
        if playbook is None:
            playbook = self.console_playbook
        runner.run_playbook(group, playbook, None, run_data, None, tags=tags, vault_password=self.vault)
        logger.debug(u'Run ansible playbook: %s' % playbook)

    @expose(aliases=[u'file-put <group> <local-file> <remote-file>'], aliases_only=True)
    @check_error
    def file_put(self):
        """Copy file to remote nodes specified by group
    - group: virtual machines group
    - cmd: shell command
        """
        group = self.get_arg(u'group')
        local_file = self.get_arg(u'local-file')
        remote_file = self.get_arg(u'remote-file')
        run_data = {
            u'tags': [u'put'],
            u'commands': {
                u'group': group,
                u'remote_file': remote_file,
                u'local_file': local_file
            }
        }
        self.__playbook(group, run_data)

    @expose(aliases=[u'file-get <group> <remote-file> <local-file>'], aliases_only=True)
    @check_error
    def file_get(self):
        """Copy file from remote nodes specified by group
    - group: virtual machines group
    - cmd: shell command
        """
        group = self.get_arg(u'group')
        remote_file = self.get_arg(u'remote-file')
        local_file = self.get_arg(u'local-file')
        run_data = {
            u'tags': [u'get'],
            u'commands': {
                u'group': group,
                u'remote_file': remote_file,
                u'local_file': local_file
            }
        }
        self.__playbook(group, run_data)

    @expose(aliases=[u'cmd <group> <cmd>'], aliases_only=True)
    @check_error
    def cmd(self):
        """Execute command on group of virtual machines
    - group: virtual machines group
    - cmd: shell command
        """
        group = self.get_arg(u'group')
        cmd = self.get_arg(u'command')
        self.__cmd(group, cmd)


class VpcServiceController(VPCaaServiceControllerChild):
    class Meta:
        label = 'vpcs'
        description = "Virtual network service management"

    @expose(aliases=[u'list [field=..]'], aliases_only=True)
    @check_error
    def list(self):
        """List all vpcs
    - field: account, ids, size, page
        - accounts: list of account id comma separated
        - ids: list of image id
        - size: number of records
        """
        data_search = {}
        data_search[u'owner-id.N'] = self.split_arg(u'accounts')
        data_search[u'vpc-id.N'] = self.split_arg(u'vpc-id.N')
        data_search[u'Nvl-MaxResults'] = self.get_arg(name=u'size', default=10, keyvalue=True)
        data_search[u'Nvl-NextToken'] = self.get_arg(name=u'page', default=0, keyvalue=True)

        uri = u'%s/computeservices/vpc/describevpcs' % self.baseuri
        res = self._call(uri, u'GET', data=urlencode(data_search, doseq=True))
        res = res.get(u'DescribeVpcsResponse')
        page = data_search[u'Nvl-NextToken']
        for item in res.get(u'vpcSet'):
            item[u'cidr'] = [u'%s' % (i[u'cidrBlock']) for i in item[u'cidrBlockAssociationSet']]
            item[u'cidr'] = u', '.join(item[u'cidr'])
        resp = {
            u'count': len(res.get(u'vpcSet')),
            u'page': page,
            u'total': res.get(u'nvl-vpcTotal'),
            u'sort': {u'field': u'id', u'order': u'asc'},
            u'instances': res.get(u'vpcSet')
        }

        headers = [u'id', u'name', u'state',  u'account', u'cidr']
        fields = [u'vpcId', u'name', u'state', u'vpcOwnerAlias', u'cidr']
        self.result(resp, key=u'instances', headers=headers, fields=fields, maxsize=40)

    @expose(aliases=[u'add <name> <account> <type>'], aliases_only=True)
    @check_error
    def add(self):
        """Create a vpc
        """
        data = {
            u'VpcName': self.get_arg(name=u'name'),
            u'owner_id': self.get_arg(name=u'account'),
            u'VpcType': self.get_arg(name=u'type')
        }
        uri = u'%s/computeservices/vpc/createvpc' % self.baseuri
        res = self._call(uri, u'POST', data={u'vpc': data}, timeout=600)
        logger.info(u'Add vpc: %s' % truncate(res))
        res = res.get(u'CreateVpcResponse').get(u'instancesSet')[0].get(u'vpcId')
        res = {u'msg': u'Add vpc %s' % res}
        self.result(res, headers=[u'msg'])


class SubnetServiceController(VPCaaServiceControllerChild):
    class Meta:
        label = 'subnets'
        description = "Subnet service management"

    @expose(aliases=[u'list [field=..]'], aliases_only=True)
    @check_error
    def list(self):
        """List all subntes
    - field: account, ids, vpcs, size, page
        - accounts: list of account id comma separated
        - ids: list of image id
        - size: number of records
        """
        data_search = {}
        data_search[u'owner-id.N'] = self.split_arg(u'accounts')
        data_search[u'subnet-id.N'] = self.split_arg(u'ids')
        data_search[u'vpc-id.N'] = self.split_arg(u'vpc-id.N')
        data_search[u'Nvl-MaxResults'] = self.get_arg(name=u'size', default=10, keyvalue=True)
        data_search[u'Nvl-NextToken'] = self.get_arg(name=u'page', default=0, keyvalue=True)

        uri = u'%s/computeservices/subnet/describesubnets' % self.baseuri
        res = self._call(uri, u'GET', data=urlencode(data_search, doseq=True))
        res = res.get(u'DescribeSubnetsResponse')
        page = data_search[u'Nvl-NextToken']
        resp = {
            u'count': len(res.get(u'subnetSet')),
            u'page': page,
            u'total': res.get(u'nvl-subnetTotal'),
            u'sort': {u'field': u'id', u'order': u'asc'},
            u'instances': res.get(u'subnetSet')
        }

        headers = [u'id', u'name', u'state',  u'account', u'availabilityZone', u'vpc', u'cidr']
        fields = [u'subnetId', u'name', u'state', u'subnetOwnerAlias', u'availabilityZone', u'vpcName', u'cidrBlock']
        self.result(resp, key=u'instances', headers=headers, fields=fields, maxsize=40)

    @expose(aliases=[u'add <name> <vpc> <availability_zone> <cidr>'], aliases_only=True)
    @check_error
    def add(self):
        """Create a subnet
        """
        data = {
            u'SubnetName': self.get_arg(name=u'name'),
            u'VpcId': self.get_arg(name=u'vpc'),
            u'AvailabilityZone': self.get_arg(name=u'availability_zone'),
            u'CidrBlock': self.get_arg(name=u'cidr')
        }
        uri = u'%s/computeservices/subnet/createsubnet' % self.baseuri
        res = self._call(uri, u'POST', data={u'subnet': data}, timeout=600)
        logger.info(u'Add subnet: %s' % truncate(res))
        res = res.get(u'CreateSubnetResponse').get(u'instancesSet')[0].get(u'subnetId')
        res = {u'msg': u'Add subnet %s' % res}
        self.result(res, headers=[u'msg'])


class SGroupServiceController(VPCaaServiceControllerChild):
    class Meta:
        label = 'securitygroups'
        description = "Security groups service management"

    @expose(aliases=[u'add <name> <vpc> [template=..]'], aliases_only=True)
    @check_error
    def add(self):
        """Create a service group
        """
        data = {
            u'GroupName': self.get_arg(name=u'name'),
            u'VpcId': self.get_arg(name=u'vpc')
        }
        sg_type = self.get_arg(name=u'template', keyvalue=True, default=None)
        if sg_type is not None:
            data[u'GroupType'] = sg_type
        uri = u'%s/computeservices/securitygroup/createsecuritygroup' % self.baseuri
        res = self._call(uri, u'POST', data={u'security_group': data}, timeout=600)
        logger.info(u'Add securitygroup: %s' % truncate(res))
        res = res.get(u'CreateSecurityGroupResponse').get(u'instancesSet')[0].get(u'groupId')
        res = {u'msg': u'Add securitygroup %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'list [field=..]'], aliases_only=True)
    @check_error
    def list(self):
        """List all security groups
    - field: account, ids, vpcs, size, page
        - accounts: list of account id comma separated
        - ids: list of image id
        - size: number of records
        """
        data_search = {}
        data_search[u'owner-id.N'] = self.split_arg(u'accounts')
        data_search[u'group-id.N'] = self.split_arg(u'ids')
        data_search[u'vpc-id.N'] = self.split_arg(u'vpcs')
        data_search[u'MaxResults'] = self.get_arg(name=u'size', default=10, keyvalue=True)
        data_search[u'NextToken'] = self.get_arg(name=u'page', default=0, keyvalue=True)

        uri = u'%s/computeservices/securitygroup/describesecuritygroups' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data_search, doseq=True))
        res = res.get(u'DescribeSecurityGroupsResponse', {})
        page = data_search[u'NextToken']

        for item in res.get(u'securityGroupInfo'):
            item[u'egress_rules'] = len(item[u'ipPermissionsEgress'])
            item[u'ingress_rules'] = len(item[u'ipPermissions'])

        resp = {
            u'count': len(res.get(u'securityGroupInfo')),
            u'page': page,
            u'total': res.get(u'nvl-securityGroupTotal'),
            u'sort': {u'field': u'id', u'order': u'asc'},
            u'instances': res.get(u'securityGroupInfo')
        }

        headers = [u'id', u'name', u'state',  u'account', u'vpc', u'egress_rules', u'ingress_rules']
        fields = [u'groupId', u'groupName', u'state', u'sgOwnerAlias', u'vpcName', u'egress_rules', u'ingress_rules']
        self.result(resp, key=u'instances', headers=headers, fields=fields, maxsize=40)

    def __format_rule(self, rules):
        for rule in rules:
            if rule[u'ipProtocol'] == u'-1':
                rule[u'ipProtocol'] = u'*'
            if rule.get(u'fromPort', None) is None or rule[u'fromPort'] == u'-1':
                rule[u'fromPort'] = u'*'
            if rule.get(u'toPort', None) is None or rule[u'toPort'] == u'-1':
                rule[u'toPort'] = u'*'
            if len(rule.get(u'groups', None)) > 0:
                group = rule[u'groups'][0]
                rule[u'groups'] = u'%s:%s [%s]' % (group[u'userName'], group[u'groupName'], group[u'groupId'])
            else:
                rule[u'groups'] = u''
            if len(rule.get(u'ipRanges', None)) > 0:
                cidr = rule[u'ipRanges'][0]
                rule[u'ipRanges'] = u'%s' % cidr[u'cidrIp']
            else:
                rule[u'ipRanges'] = u''
        return rules

    @expose(aliases=[u'get <id>'], aliases_only=True)
    @check_error
    def get(self):
        """Get service group with rules
        """
        value = self.get_arg(u'id')
        data_search = {u'GroupId.N': [value]}
        uri = u'%s/computeservices/securitygroup/describesecuritygroups' % self.baseuri
        res = self._call(uri, u'GET', data=urllib.urlencode(data_search, doseq=True))
        res = res.get(u'DescribeSecurityGroupsResponse').get(u'securityGroupInfo', [])
        if len(res) == 0:
            raise Exception(u'Security group %s does not exist' % value)
        res = res[0]
        egress_rules = self.__format_rule(res.pop(u'ipPermissionsEgress'))
        ingress_rules = self.__format_rule(res.pop(u'ipPermissions'))
        fields = [u'groups', u'ipRanges', u'ipProtocol', u'fromPort', u'toPort', u'reserved']
        self.result(res, details=True, maxsize=40)
        self.app.print_output(u'Egress rules: ')
        self.result(egress_rules, headers=[u'toSecuritygroup', u'toCidr', u'protocol', u'fromPort', u'toPort',
                                           u'reserved'], fields=fields, maxsize=80)
        self.app.print_output(u'Ingress rules: ')
        self.result(ingress_rules, headers=[u'fromSecuritygroup', u'fromCidr', u'protocol', u'fromPort', u'toPort',
                                            u'reserved'], fields=fields, maxsize=80)

    @expose(aliases=[u'delete <uuid>'], aliases_only=True)
    @check_error
    def delete(self):
        """Delete a service group
        """
        data = {
            u'GroupName': self.get_arg(name=u'uuid')
        }
        uri = u'%s/computeservices/securitygroup/deletesecuritygroup' % self.baseuri
        res = self._call(uri, u'DELETE', data={u'security_group': data}, timeout=600)
        logger.info(u'Add securitygroup: %s' % truncate(res))
        res = res.get(u'DeleteSecurityGroupResponse').get(u'return')
        res = {u'msg': u'Delete securitygroup %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'add-rule <type> <group> <dest/source> [proto=..] [port:..]'], aliases_only=True)
    @check_error
    def add_rule(self):
        """Add egress rule
    - type: egress or ingress. For egress group is the source and specify the destination. For ingress group is the
      destination and specify the source.
    - proto: ca be tcp, udp, icmp or -1 for all. [default=-1]
    - port: can be an integer between 0 and 65535 or a range with start and end in the same interval. Range format
      is <start>-<end>. Use -1 for all ports. [default=-1]
    - dest/source: rule destination. Syntax <type>:<value>.
    Source and destination type can be SG, CIDR. For SG value must be <sg_id>. For CIDR value should like
    10.102.167.0/24.
        """
        rule_type = self.get_arg(name=u'type')
        group_id = self.get_arg(name=u'group')
        dest = self.get_arg(name=u'dest/source').split(u':')
        port = self.get_arg(name=u'port', default=None, keyvalue=True)
        proto = self.get_arg(name=u'proto', default=u'-1', keyvalue=True)
        from_port = -1
        to_port = -1
        if port is not None:
            port = port.split(u'-')
            if len(port) == 1:
                from_port = to_port = port[0]
            else:
                from_port, to_port = port

        if len(dest) <= 0 or len(dest) > 2:
            raise Exception(u'Source/destination syntax is wrong')
        if dest[0] not in [u'SG', u'CIDR']:
            raise Exception(u'Source/destination type can be only SG or CIDR')
        data = {
            u'GroupId': group_id,
            u'IpPermissions.N': [
                {
                    u'FromPort': from_port,
                    u'ToPort': to_port,
                    u'IpProtocol': proto
                }
            ]
        }
        if dest[0] == u'SG':
            data[u'IpPermissions.N'][0][u'UserIdGroupPairs'] = [{
                u'GroupId': dest[1]
            }]
        elif dest[0] == u'CIDR':
            data[u'IpPermissions.N'][0][u'IpRanges'] = [{
                u'CidrIp': dest[1]
            }]
        else:
            raise Exception(u'Wrong rule type')

        if rule_type == u'egress':
            uri = u'%s/computeservices/securitygroup/authorizesecuritygroupegress' % self.baseuri
            key = u'AuthorizeSecurityGroupEgressResponse'
        elif rule_type == u'ingress':
            uri = u'%s/computeservices/securitygroup/authorizesecuritygroupingress' % self.baseuri
            key = u'AuthorizeSecurityGroupIngressResponse'
        res = self._call(uri, u'POST', data={u'rule': data}, timeout=600)
        logger.info(u'Add securitygroup rule: %s' % truncate(res))
        res = res.get(key).get(u'Return')
        res = {u'msg': u'Create securitygroup rule %s' % res}
        self.result(res, headers=[u'msg'])

    @expose(aliases=[u'del-rule <type> <group> <dest/source> [proto=..] [port:..]'], aliases_only=True)
    @check_error
    def del_rule(self):
        """Add egress rule
    - type: egress or ingress. For egress group is the source and specify the destination. For ingress group is the
      destination and specify the source.
    - proto: ca be tcp, udp, icmp or -1 for all. [default=-1]
    - port: can be an integer between 0 and 65535 or a range with start and end in the same interval. Range format
      is <start>-<end>. Use -1 for all ports. [default=-1]
    - dest/source: rule destination. Syntax <type>:<value>.
    Source and destination type can be SG, CIDR. For SG value must be <sg_id>. For CIDR value should like
    10.102.167.0/24.
        """
        rule_type = self.get_arg(name=u'type')
        group_id = self.get_arg(name=u'group')
        dest = self.get_arg(name=u'dest/source').split(u':')
        port = self.get_arg(name=u'port', default=None, keyvalue=True)
        proto = self.get_arg(name=u'proto', default=u'-1', keyvalue=True)
        from_port = -1
        to_port = -1
        if port is not None:
            port = port.split(u'-')
            if len(port) == 1:
                from_port = to_port = port[0]
            else:
                from_port, to_port = port

        if len(dest) <= 0 or len(dest) > 2:
            raise Exception(u'Source/destination syntax is wrong')
        if dest[0] not in [u'SG', u'CIDR']:
            raise Exception(u'Source/destination type can be only SG or CIDR')
        data = {
            u'GroupId': group_id,
            u'IpPermissions.N': [
                {
                    u'FromPort': from_port,
                    u'ToPort': to_port,
                    u'IpProtocol': proto
                }
            ]
        }
        if dest[0] == u'SG':
            data[u'IpPermissions.N'][0][u'UserIdGroupPairs'] = [{
                u'GroupId': dest[1]
            }]
        elif dest[0] == u'CIDR':
            data[u'IpPermissions.N'][0][u'IpRanges'] = [{
                u'CidrIp': dest[1]
            }]
        else:
            raise Exception(u'Wrong rule type')

        if rule_type == u'egress':
            uri = u'%s/computeservices/securitygroup/revokesecuritygroupegress' % self.baseuri
            key = u'RevokeSecurityGroupEgressResponse'
        elif rule_type == u'ingress':
            uri = u'%s/computeservices/securitygroup/revokesecuritygroupingress' % self.baseuri
            key = u'RevokeSecurityGroupIngressResponse'
        res = self._call(uri, u'DELETE', data={u'rule': data}, timeout=600)
        logger.info(u'Delete securitygroup rules: %s' % truncate(res))
        res = res.get(key).get(u'Return')
        res = {u'msg': u'Delete securitygroup rules %s' % res}
        self.result(res, headers=[u'msg'])


vpcaas_controller_handlers = [
    VPCaaServiceController,    
    VMServiceController,
    ImageServiceController,
    VpcServiceController,
    SubnetServiceController,
    SGroupServiceController
] 
