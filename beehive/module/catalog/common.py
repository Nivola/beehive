'''
Created on May 20, 2016

@author: darkbk
'''
import ujson as json
from beecell.simple import id_gen, str2uni

class CatalogEndpoint(object):
    """Catalog endpoint.
    
    :param name: node name
    :param desc: node desc
    :param nodetype: node type. Ex. cloudapi, cloudportal, mysql, redis
    :param connection: node connection
    :param refresh: node refresh: Can be static or dynamic
    :param creation: creation date [optional]
    :param modified: modification date [optional]
    :param action: node action [optional]
    :param id: node id [optional]
    """
        
    def __init__(self, name, desc, service, catalog, uri, creation=None,
                 modified=None, enabled=True, oid=None):
        if oid is not None:
            self.id = oid
        else:
            self.id = id_gen()         
        self.name = name
        self.desc = desc
        self.service = service
        self.catalog_id = catalog
        self.uri = uri
        self.enabled = enabled 
        self.creation = creation
        self.modified = modified

    def __str__(self):
        res = "<Node id=%s, name=%s, service=%s, catalog=%s>" % \
                (self.id, self.name, self.service, self.catalog_id)
        return res

    def dict(self):
        """Return dict representation.
        
        :return: dict
        
            .. code-block:: python
            
                {"id":.., 
                 "name":.., 
                 "desc":.., 
                 "service":.., 
                 "catalog":.., 
                 "uri":..,
                 "enabled":..}
        """
        if self.creation is not None:
            creation = str2uni(self.creation.strftime(u'%d-%m-%y %H:%M:%S'))
        else:
            creation = None
        if self.modified is not None:
            modified = str2uni(self.modified.strftime(u'%d-%m-%y %H:%M:%S'))
        else:
            modified = None            
        msg = {
            u'id':self.id, 
            u'name':self.name, 
            u'desc':self.desc,
            u'service':self.service,
            u'date':{u'creation':creation, u'modified':modified},
            u'catalog':self.catalog_id,
            u'uri':self.uri,
            u'enabled':self.enabled
        }
        return msg      

    def json(self):
        """Return json representation.
        
        :return: json string
        
            .. code-block:: python
            
                {"id":.., 
                 "name":.., 
                 "desc":.., 
                 "service":.., 
                 "catalog":.., 
                 "uri":..,
                 "enabled":..}
        """
        if self.creation is not None:
            creation = str2uni(self.creation.strftime(u'%d-%m-%y %H:%M:%S'))
        else:
            creation = None
        if self.modified is not None:
            modified = str2uni(self.modified.strftime(u'%d-%m-%y %H:%M:%S'))
        else:
            modified = None            
        msg = {
            u'id':self.id, 
            u'name':self.name, 
            u'desc':self.desc,
            u'service':self.service,
            u'date':{u'creation':creation, u'modified':modified},
            u'catalog':self.catalog_id,
            u'uri':self.uri,
            u'enabled':self.enabled
        }
        return json.dumps(msg)