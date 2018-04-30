"""
Created on Nov 20, 2017

@author: darkbk
"""
import logging
import urllib

import copy
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController
from re import match
from beecell.simple import truncate

logger = logging.getLogger(__name__)


class BusinessController(BaseController):
    class Meta:
        label = 'business'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Business Service and Authority Management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)


class ConnectionHelper(object):
    @staticmethod
    def format_name(name, account_id):
        """"""
        return u'%s-%s' % (name, account_id)

    @staticmethod
    def get_org(ctrl, value):
        return ctrl._call(u'/v1.0/nws/organizations/%s' % value, u'GET').get(u'organization')

    @staticmethod
    def get_div(ctrl, value):
        return ctrl._call(u'/v1.0/nws/divisions/%s' % value, u'GET').get(u'division')

    @staticmethod
    def get_account(ctrl, value):
        return ctrl._call(u'/v1.0/nws/accounts/%s' % value, u'GET').get(u'account')

    @staticmethod
    def get_catalog(ctrl, value):
        return ctrl._call(u'/v1.0/nws/srvcatalogs/%s' % value, u'GET').get(u'catalog')

    @staticmethod
    def service_instance_exist(ctrl, type, name):
        """Check service instance with this name exists"""
        uri = u'/v1.0/nws/serviceinsts'
        res = ctrl._call(uri, u'GET', data=u'name=%s' % name)
        logger.info(u'Get service instance by name: %s' % res)
        count = res.get(u'count')
        if count > 0:
            ctrl.output(u'Service %s %s already exists' % (type, name))
            return True

        return False

    @staticmethod
    def get_service_instance(ctrl, name):
        """Check service instance with this name exists"""
        uri = u'/v1.0/nws/serviceinsts'
        res = ctrl._call(uri, u'GET', data=u'name=%s' % name)
        logger.info(u'Get service instance by name: %s' % res)
        count = res.get(u'count')
        if count > 1:
            raise Exception(u'Service instance %s does not exist' % name)

        return res.get(u'serviceinsts')[0][u'uuid']

    @staticmethod
    def get_service_def(ctrl, name):
        """Check service definition with this name exists"""
        uri = u'/v1.0/nws/servicedefs'
        res = ctrl._call(uri, u'GET', data=u'name=%s' % name)
        logger.info(u'Get service definition by name: %s' % res)
        count = res.get(u'count')
        if count < 1:
            raise Exception(u'Template %s does not exist' % name)

        return res.get(u'servicedefs')[0][u'uuid']

    @staticmethod
    def get_service_instances(ctrl, filter=u''):
        """Get account service instances tree.
        """
        data = u''
        uri = u'/v1.0/nws/serviceinsts'

        if ctrl.format == u'tree':
            filter += u'&size=100'
            res = ctrl._call(uri, u'GET', data=filter)
            logger.info(res)
            res = res.get(u'serviceinsts', [])
            def get_tree_alias(data):
                return u'[%s] %s' % (data[u'uuid'], data[u'name'])

            index = {i[u'uuid']: {get_tree_alias(i): {}} for i in res}

            tree = {}
            for item in res:
                parent = item[u'parent']
                idx_item = index[item[u'uuid']]
                # idx_childs = index[item[u'uuid']].values()[0]
                if parent.has_key(u'uuid'):
                    index[parent[u'uuid']].values()[0].update(idx_item)
                if parent == {}:
                    tree.update(idx_item)
            ctrl.result({u'services': tree})
        else:
            res = ctrl._call(uri, u'GET', data=filter)
            logger.info(res)
            fields = [u'id', u'uuid', u'name', u'version', u'service_definition_id', u'status', u'active',
                      u'resource_uuid', u'is_container', u'parent.name', u'date.creation']
            headers = [u'id', u'uuid', u'name', u'version', u'definition', u'status', u'active', u'resource',
                       u'is_container', u'parent', u'creation']
            ctrl.result(res, key=u'serviceinsts', headers=headers, fields=fields)

    @staticmethod
    def create_image(ctrl, account=None, name=None, template=None, **kvargs):
        data = {
            u'ImageName': ConnectionHelper.format_name(name, account),
            u'owner_id': account,
            u'ImageType': ConnectionHelper.get_service_def(ctrl, template)
        }
        uri = u'/v1.0/nws/computeservices/image/createimage'
        res = ctrl._call(uri, u'POST', data={u'image': data}, timeout=600)
        logger.info(u'Add image: %s' % truncate(res))
        res = res.get(u'CreateImageResponse').get(u'instancesSet')[0].get(u'imageId')
        ctrl.output(u'Create image %s' % res)
        return res

    @staticmethod
    def create_vpc(ctrl, account=None, name=None, template=None, **kvargs):
        data = {
            u'VpcName': ConnectionHelper.format_name(name, account),
            u'owner_id': account,
            u'VpcType': ConnectionHelper.get_service_def(ctrl, template)
        }
        uri = u'/v1.0/nws/computeservices/vpc/createvpc'
        res = ctrl._call(uri, u'POST', data={u'vpc': data}, timeout=600)
        logger.info(u'Add vpc: %s' % truncate(res))
        res = res.get(u'CreateVpcResponse').get(u'instancesSet')[0].get(u'vpcId')
        ctrl.output(u'Create vpc %s' % res)
        return res

    @staticmethod
    def create_subnet(ctrl, account=None, name=None, vpc=None, zone=None, cidr=None, **kvargs):
        vpc_name = ConnectionHelper.format_name(vpc, account)
        vpc_uuid = ConnectionHelper.get_service_instance(ctrl, vpc_name)
        data = {
            u'SubnetName': ConnectionHelper.format_name(name, account),
            u'VpcId': vpc_uuid,
            u'AvailabilityZone': zone,
            u'CidrBlock': cidr
        }
        uri = u'/v1.0/nws/computeservices/subnet/createsubnet'
        res = ctrl._call(uri, u'POST', data={u'subnet': data}, timeout=600)
        logger.info(u'Add subnet: %s' % truncate(res))
        res = res.get(u'CreateSubnetResponse').get(u'instancesSet')[0].get(u'subnetId')
        ctrl.output(u'Create subnet %s' % res)
        return res

    @staticmethod
    def create_sg(ctrl, account=None, name=None, vpc=None, template=None, **kvargs):
        vpc_name = ConnectionHelper.format_name(vpc, account)
        vpc_uuid = ConnectionHelper.get_service_instance(ctrl, vpc_name)
        data = {
            u'GroupName': ConnectionHelper.format_name(name, account),
            u'VpcId': vpc_uuid
        }
        if template is not None:
            data[u'GroupType'] = ConnectionHelper.get_service_def(ctrl, template)
        uri = u'/v1.0/nws/computeservices/securitygroup/createsecuritygroup'
        res = ctrl._call(uri, u'POST', data={u'security_group': data}, timeout=600)
        logger.info(u'Add security group: %s' % truncate(res))
        res = res.get(u'CreateSecurityGroupResponse').get(u'instancesSet')[0].get(u'groupId')
        ctrl.output(u'Create security group %s' % res)
        return res

    @staticmethod
    def get_roles(ctrl, name):
        ctrl.subsystem = u'auth'

        roles = ctrl._call(u'/v1.0/nas/roles', u'GET', data=urllib.urlencode({u'names': name})).get(u'roles', [])
        logger.debug(u'Get roles: %s' % truncate(roles))
        headers = [u'id', u'uuid', u'name', u'active', u'date.creation', u'date.modified', u'date.expiry']
        ctrl.result(roles, headers=headers)

        for role in roles:
            role_name = role.get(u'name')
            users = ctrl._call(u'/v1.0/nas/users', u'GET', data=urllib.urlencode({u'role': role_name}))\
                .get(u'users', [])
            logger.debug(u'Get role %s users: %s' % (role_name, truncate(users)))
            ctrl.output(u'Role %s users' % role_name)
            ctrl.result(users, headers=headers)

        ctrl.subsystem = u'service'

        return roles

    @staticmethod
    def set_role(ctrl, role, user, op=u'append'):
        """Append/remove role to/from a user

        :param ctrl: cement controller reference
        :param role: role id, uuid or name
        :param user: user id, uuid or name
        :param op: append or remove
        :return:
        """
        ctrl.subsystem = u'auth'

        if op == u'append':
            role = (role, u'2099-12-31')
        data = {
            u'user': {
                u'roles': {
                    op: [role]
                },
            }
        }
        uri = u'/v1.0/nas/users/%s' % user
        res = ctrl._call(uri, u'PUT', data=data)
        logger.info(u'%s user %s role %s' % (op, user, role))
        ctrl.result({u'msg': u'%s user %s role %s' % (op, user, role)})

        ctrl.subsystem = u'service'

    @staticmethod
    def add_role(ctrl, name, desc, perms):
        ctrl.subsystem = u'auth'

        # add role
        try:
            data = {
                u'role': {
                    u'name': name,
                    u'desc': desc
                }
            }
            uri = u'/v1.0/nas/roles'
            role = ctrl._call(uri, u'POST', data=data)
            logger.info(u'Add role: %s' % role)
            ctrl.output(u'Add role: %s' % role)
        except Exception as ex:
            uri = u'/v1.0/nas/roles/%s' % name
            role = ctrl._call(uri, u'GET', data=u'').get(u'role')
            logger.info(u'Role %s already exists' % role.get(u'name'))
            ctrl.output(u'Role %s already exists' % role.get(u'name'))

        # add role permissions
        # for perm in perms:
        data = {
            u'role': {
                u'perms': {
                    u'append': perms,
                    u'remove': []
                }
            }
        }
        uri = u'/v1.0/nas/roles/%s' % role[u'uuid']
        res = ctrl._call(uri, u'PUT', data=data)
        logger.info(u'Add role perms %s' % perms)
        ctrl.output(u'Add role perms')

        ctrl.subsystem = u'service'

        return role[u'uuid']

    @staticmethod
    def set_perms_objid(perms, objid):
        new_perms = []
        for perm in perms:
            if perm.get(u'objid').find(u'<objid>') >= 0:
                new_perm = copy.deepcopy(perm)
                new_perm[u'objid'] = new_perm[u'objid'].replace(u'<objid>', objid)
                new_perms.append(new_perm)
        return new_perms


class SpecializedServiceControllerChild(ApiController):
    def is_name(self, oid):
        """Check if id is uuid, id or literal name.

        :param oid:
        :return: True if it is a literal name
        """
        # get obj by uuid
        if match(u'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(oid)):
            logger.debug(u'Param %s is an uuid' % oid)
            return False
        # get obj by id
        elif match(u'^\d+$', str(oid)):
            logger.debug(u'Param %s is an id' % oid)
            return False
        # get obj by name
        elif match(u'[\-\w\d]+', oid):
            logger.debug(u'Param %s is a name' % oid)
            return True

    def get_account(self, oid):
        """"""
        check = self.is_name(oid)
        if check is True:
            uri = u'%s/accounts' % self.baseuri
            res = self._call(uri, u'GET', data=u'name=%s' % oid)
            logger.info(u'Get account by name: %s' % res)
            count = res.get(u'count')
            if count > 1:
                raise Exception(u'There are some account with name %s. Select one using uuid' % oid)

            return res.get(u'accounts')[0][u'uuid']
        return oid

    def get_service_def(self, oid):
        """"""
        check = self.is_name(oid)
        if check is True:
            uri = u'%s/servicedefs' % self.baseuri
            res = self._call(uri, u'GET', data=u'name=%s' % oid)
            logger.info(u'Get account by name: %s' % res)
            count = res.get(u'count')
            if count > 1:
                raise Exception(u'There are some template with name %s. Select one using uuid' % oid)
            if count == 0:
                raise Exception(u'%s does not exist or you are not authorized to see it' % oid)

            return res.get(u'servicedefs')[0][u'uuid']
        return oid

    def get_service_instance(self, oid, account_id=None):
        """"""
        check = self.is_name(oid)
        if check is True:
            uri = u'%s/serviceinsts' % self.baseuri
            data = u'name=%s' % oid
            if account_id is not None:
                data += u'&account_id=%s' % account_id
            res = self._call(uri, u'GET', data=u'name=%s' % oid)
            logger.info(u'Get account by name: %s' % res)
            count = res.get(u'count')
            if count > 1:
                raise Exception(u'There are some service with name %s. Select one using uuid' % oid)
            if count == 0:
                raise Exception(u'%s does not exist or you are not authorized to see it' % oid)

            return res.get(u'serviceinsts')[0][u'uuid']
        return oid


business_controller_handlers = [
    BusinessController
]
