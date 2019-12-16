# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

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
        
    def __init__(self, name, desc, service, catalog, uri, creation=None, modified=None, enabled=True, oid=None):
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
            creation = str2uni(self.creation.strftime('%d-%m-%y %H:%M:%S'))
        else:
            creation = None
        if self.modified is not None:
            modified = str2uni(self.modified.strftime('%d-%m-%y %H:%M:%S'))
        else:
            modified = None            
        msg = {
            'id': self.id,
            'name': self.name,
            'desc': self.desc,
            'service': self.service,
            'date': {'creation': creation, 'modified': modified},
            'catalog': self.catalog_id,
            'uri': self.uri,
            'enabled': self.enabled
        }
        return msg.decode('utf-8')

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
            creation = str2uni(self.creation.strftime('%d-%m-%y %H:%M:%S'))
        else:
            creation = None
        if self.modified is not None:
            modified = str2uni(self.modified.strftime('%d-%m-%y %H:%M:%S'))
        else:
            modified = None            
        msg = {
            'id':self.id, 
            'name':self.name, 
            'desc':self.desc,
            'service':self.service,
            'date':{'creation':creation, 'modified':modified},
            'catalog':self.catalog_id,
            'uri':self.uri,
            'enabled':self.enabled
        }
        return json.dumps(msg)