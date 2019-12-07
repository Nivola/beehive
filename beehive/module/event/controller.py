# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

import logging
from datetime import datetime, timedelta

from beecell.perf import watch
from beecell.simple import str2uni, id_gen, truncate, format_date
import ujson as json
from beehive.common.apimanager import ApiController, ApiManagerError,\
    ApiViewResponse, ApiObject
from beehive.module.event.model import EventDbManager
from beecell.db import QueryError
from beehive.common.data import trace


class EventController(ApiController):
    """Event Module controller.
    """    
    version = 'v1.0'
    
    def __init__(self, module):
        ApiController.__init__(self, module)

        self.event_manager = EventDbManager()
        
        self.child_classes = [GenericEvent]
    
    @trace(entity='GenericEvent', op='view')
    def get_event(self, oid):
        """Get single event.

        :param oid: entity model id, name or uuid         
        :return: Catalog
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify base permissions
        self.check_authorization(GenericEvent.objtype, GenericEvent.objdef, '*', 'view')
        
        # get entity
        entity = self.event_manager.get_event(oid)
        obj = BaseEvent(entity)
        
        # verify event specific permissions
        self.check_authorization(entity.objtype, entity.objdef, entity.objid, 'view')
        
        return obj
    
    @trace(entity='GenericEvent', op='view')
    def get_events(self, page=0, size=10, order='DESC', field='id', *args, **kvargs):
        """Get events with pagination

        :param type: event type [optional]
        :param objid: objid [optional]
        :param objtype: objtype [optional]
        :param objdef: objdef [optional]
        :param data: event data [optional]
        :param source: event source [optional]
        :param dest: event destinatiaion [optional]
        :param datefrom: event data from. Ex. '1985-04-12T23:20:50.52Z' [optional]
        :param dateto: event data to. Ex. '1985-04-12T23:20:50.52Z' [optional]
        :param page: objects list page to show [default=0]
        :param size: number of objects to show in list per page [default=0]
        :param order: sort order [default=DESC]
        :param field: sort field [default=id]
        :param args: custom params
        :param kvargs: custom params
        :return: (list of entity_class instances, total)
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify permissions
        self.check_authorization(GenericEvent.objtype, GenericEvent.objdef, '*', 'view')
        
        res = []
        
        # verify permissions
        objtype = kvargs.get('objtype', None)
        definition = kvargs.get('objdef', None)
        objs = self.can('use', objtype=objtype, definition=definition)

        # set max time window to 2 hours
        if kvargs.get('datefrom', None) is None:
            kvargs['datefrom'] = datetime.today() - timedelta(hours=2)
        elif kvargs.get('datefrom', None) is not None:
            if kvargs.get('dateto', None) is None or \
               kvargs['dateto'] <= kvargs.get('datefrom') or \
               kvargs['dateto'] > kvargs.get('datefrom') + timedelta(hours=2):
                kvargs['dateto'] = kvargs.get('datefrom') + timedelta(hours=2)

        # create permission tags
        tags = []
        for objdef, perms in objs.items():
            for perm in perms:
                tags.append(self.event_manager.hash_from_permission(objdef, perm))
        self.logger.debug('Permission tags to apply: %s' % truncate(tags))
                
        try:
            entities, total = self.event_manager.get_events(tags=tags, page=page, size=size, order=order, field=field,
                                                            with_perm_tag=False, *args, **kvargs)
            
            for entity in entities:
                obj = BaseEvent(entity)
                res.append(obj)

            self.logger.debug('Get events (total:%s): %s' % (total, truncate(res)))
            return res, total
        except QueryError as ex:         
            self.logger.warn(ex)
            return [], 0

    @trace(entity='GenericEvent', op='view')
    def get_event_types(self):
        """Get event types.
      
        :return: List of event types
        :rtype: list
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """        
        # verify permissions
        self.check_authorization(GenericEvent.objtype, GenericEvent.objdef, '*', 'view')
        
        # get available event types
        try:
            res = set(self.event_manager.get_types())
        except QueryError as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex)
        
        #res = event_types_available.intersection(event_types)
            
        self.logger.debug('Get event types: %s' % res)
        return res
    
    @trace(entity='GenericEvent', op='view')
    def get_entity_definitions(self):
        """Get event entity definition. 
      
        :return: List of entity definitions
        :rtype: list
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """        
        # verify permissions
        objs = self.can('view')
        event_types = set(objs.keys())
        
        # get available event types
        try:
            event_types_available = set(self.event_manager.get_entity_definitions())
        except QueryError as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex)
        
        res = event_types_available.intersection(event_types)
            
        self.logger.debug('Get event entity definitions: %s' % res)
        return res


class GenericEvent(ApiObject):
    objtype = 'event'
    objdef = 'GenericEvent'
    objdesc = 'Generic Event'


class BaseEvent(object):
    def __init__(self, event):
        self.logger = logging.getLogger(self.__class__.__module__+'.'+self.__class__.__name__)

        self.event = event
    
    def info(self):
        """
        """
        data = {}
        try:
            data = json.loads(self.event.data)
        except Exception as ex:
            self.logger.warn('Can not parse event %s data' % self.event.id)
                            
        obj = {'id': self.event.id,
               'event_id': self.event.event_id,
               'type': self.event.type,
               'objid': self.event.objid,
               'objdef': self.event.objdef,
               'objtype': self.event.objtype,
               'date': format_date(self.event.creation, microsec=True),
               'data': data,
               'source': json.loads(self.event.source),
               'dest': json.loads(self.event.dest)}
        return obj
    
    def detail(self):
        """
        """
        return self.info()
