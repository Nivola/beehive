'''
Created on Jan 11, 2016

@author: darkbk
'''
perms = [
(1, 1, 'auth', 'objects', 'ObjectContainer', '*', 1, '*'),
(1, 1, 'auth', 'role', 'RoleContainer', '*', 1, '*'),
(1, 1, 'auth', 'user', 'UserContainer', '*', 1, '*'),

(1, 1, 'directory', 'catalog', '', '*', 1, '*'),
(1, 1, 'directory', 'catalog.service', '', '*//*', 1, '*'),

(1, 1, 'config', 'property', 'ConfigContainer', '*', 1, '*'),
(1, 1, 'container', 'cloudstack', 'CloudstackContainer', '*', 1, '*'),
(1, 1, 'admin', 'jobs', 'ObjectContainer', '*', 1, '*'),

(1, 1, 'process', 'process', 'Process', '*', 1, '*'),
(1, 1, 'process', 'process_inst', 'ProcessInstance', '*', 1, '*'),
(1, 1, 'process', 'process_inst.task_inst', 'taskInstance', '*//*', 1, '*'),
(1, 1, 'process', 'process_inst.task_inst', 'taskInstance', '*//*', 1, '*'),

(1, 1, 'container', 'openstack', 'OpenstackContainer', '*', 1, '*'),
(1, 1, 'resource', 'openstack.domain', 'OpenstackDomain', '*', 1, '*'),
(1, 1, 'resource', 'openstack.domain.project', 'OpenstackProject', '*', 1, '*'),
(1, 1, 'resource', 'openstack.domain.project.instance', 'OpenstackInstance', '*', 1, '*'),
(1, 1, 'resource', 'openstack.domain.project.volume', 'OpenstackVolume', '*', 1, '*'),
(1, 1, 'resource', 'openstack.domain.project.network', 'OpenstackNetwork', '*', 1, '*'),
(1, 1, 'resource', 'openstack.domain.project.router', 'OpenstackRouter', '*', 1, '*'),
(1, 1, 'resource', 'openstack.image', 'OpenstackImage', '*', 1, '*'),
(1, 1, 'resource', 'openstack.flavor', 'OpenstackFlavor', '*', 1, '*'),
           
(1, 1, 'container', 'cloudstack', 'CloudstackContainer', '*', 1, '*'),
(1, 1, 'resource', 'cloudstack.org', 'CloudstackOrg', '*//*', 1, '*'),
(1, 1, 'resource', 'cloudstack.org.grp', 'CloudstackGrp', '*//*//*', 1, '*'),
(1, 1, 'resource', 'cloudstack.org.grp.vm', 'CloudstackVm', '*//*//*//*', 1, '*'),
(1, 1, 'resource', 'cloudstack.org.grp.sdn', 'CloudstackSdn', '*//*//*//*', 1, '*'),
(1, 1, 'resource', 'cloudstack.org.grp.volume', 'CloudstackVolume', '*//*//*//*', 1, '*'),
(1, 1, 'resource', 'cloudstack.offering', 'CloudstackOffering', '*//*', 1, '*'),
(1, 1, 'resource', 'cloudstack.template', 'CloudstackTemplate', '*//*', 1, '*'),
(1, 1, 'resource', 'cloudstack.iso', 'CloudstackIso', '*//*', 1, '*'),

(1, 1, 'container', 'vsphere', 'VsphereContainer', '*', 1, '*'),
(1, 1, 'resource', 'vsphere.folder', 'VsphereFolder', '*//*', 1, '*'),
(1, 1, 'resource', 'vsphere.instance', 'VsphereInstance', '*//*', 1, '*'),
(1, 1, 'resource', 'vsphere.network', 'VsphereNetwork', '*//*', 1, '*'),
(1, 1, 'resource', 'vsphere.dvs', 'VsphereDvs', '*//*', 1, '*'),
(1, 1, 'resource', 'vsphere.dvp', 'VsphereDvp', '*//*', 1, '*'),
(1, 1, 'resource', 'vsphere.host', 'VsphereHost', '*//*', 1, '*'),
(1, 1, 'resource', 'vsphere.cluster', 'VsphereCluster', '*//*', 1, '*'),
(1, 1, 'resource', 'vsphere.resourcepool', 'VsphereResourcePool', '*//*', 1, '*'),
(1, 1, 'resource', 'vsphere.datastore', 'VsphereDatastore', '*//*', 1, '*'),         


(1, 1, 'service', 'virtual_desktop', 'VirtualDesktopService', '*', 1, '*'),
(1, 1, 'service', 'virtual_desktop.instance', 'ServiceInstance', '*//*', 1, '*'),
]