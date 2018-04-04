"""
Created on Nov 20, 2017

@author: darkbk
"""
import logging
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
        if count > 1:
            raise Exception(u'Template %s does not exist' % name)

        return res.get(u'servicedefs')[0][u'uuid']

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
        uri = u'/v1.0/nws/computeservices/securitygroup/createsecuritygroup2'
        res = ctrl._call(uri, u'POST', data={u'security_group': data}, timeout=600)
        logger.info(u'Add security group: %s' % truncate(res))
        res = res.get(u'CreateSecurityGroupResponse').get(u'instancesSet')[0].get(u'groupId')
        ctrl.output(u'Create security group %s' % res)
        return res


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

            return res.get(u'servicedefs')[0][u'uuid']
        return oid

    def get_service_instance(self, oid):
        """"""
        check = self.is_name(oid)
        if check is True:
            uri = u'%s/serviceinsts' % self.baseuri
            res = self._call(uri, u'GET', data=u'name=%s' % oid)
            logger.info(u'Get account by name: %s' % res)
            count = res.get(u'count')
            if count > 1:
                raise Exception(u'There are some service with name %s. Select one using uuid' % oid)

            return res.get(u'serviceinsts')[0][u'uuid']
        return oid


business_controller_handlers = [
    BusinessController
]
