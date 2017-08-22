'''
Created on Dec 31, 2014

@author: darkbk
'''
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
    version = u'v1.0'
    
    def __init__(self, module):
        ApiController.__init__(self, module)

        self.event_manager = EventDbManager()
        
        self.child_classes = [GenericEvent]
    
    @trace(entity=u'GenericEvent', op=u'view')
    def get_event(self, oid):
        """Get single event.

        :param oid: entity model id, name or uuid         
        :return: Catalog
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """
        # verify base permissions
        self.check_authorization(GenericEvent.objtype, GenericEvent.objdef, 
                                 u'*', u'view')        
        
        # get entity
        entity = self.event_manager.get_event(oid)
        
        # verify event specific permissions
        self.check_authorization(entity.objtype, entity.objdef, 
                                 entity.objid, u'view')          
        
        return entity
    
    @trace(entity=u'GenericEvent', op=u'view')
    def get_events(self, page=0, size=10, order=u'DESC', field=u'id', 
                   *args, **kvargs):
        """Get events with pagination

        :param type: list of event type [optional]
        :param objid: objid [optional]
        :param objtype: objtype [optional]
        :param objdef: objdef [optional]
        :param data: event data [optional]
        :param source: event source [optional]
        :param dest: event destinatiaion [optional]
        :param datefrom: event data from. Ex. '2015-3-9-15-23-56' [optional]
        :param dateto: event data to. Ex. '2015-3-9-15-23-56' [optional]
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
        self.check_authorization(GenericEvent.objtype, GenericEvent.objdef, 
                                 u'*', u'view')
        
        res = []
        
        # verify permissions
        objs = self.can(u'use')
        self.logger.warn(objs)

        # create permission tags
        tags = []
        for objdef, perms in objs.items():
            for perm in perms:
                tags.append(self.event_manager.hash_from_permission(objdef, perm))
        self.logger.debug(u'Permission tags to apply: %s' % tags)
                
        try:
            entities, total = self.event_manager.get_events(
                tags=tags, page=page, size=size, order=order, field=field, 
                *args, **kvargs)
            
            for entity in entities:
                obj = BaseEvent(entity)
                res.append(obj)

            self.logger.debug(u'Get events (total:%s): %s' % (total, truncate(res)))
            return res, total
        except QueryError as ex:         
            self.logger.warn(ex)
            return [], 0    
    
    '''
    @trace(entity=u'GenericEvent', op=u'view')
    def get_events2(self, oid=None, etype=None, data=None, 
                         source=None, dest=None, datefrom=None, dateto=None,
                         page=0, size=10, objid=None, objdef=None, objtype=None):
        """Get events.

        :param oid str: event oid [optional]
        :param etype str: list of event type [optional]
        :param data str: event data [optional]
        :param source str: event source [optional]
        :param dest str: event destinatiaion [optional]
        :param datefrom: event data from. Ex. '2015-3-9-15-23-56' [optional]
        :param dateto: event data to. Ex. '2015-3-9-15-23-56' [optional]
        :param page: event list page to show [default=0]
        :param size: number of event to show in list per page [default=0]
        :param objid str: entity id [optional]
        :param objtype str: entity type [optional]
        :param objdef str: entity definition [optional]
        :return: List of events (id, type, objid, creation, data, source, dest)
        :rtype: list of tuple
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """        
        # verify permissions
        if etype is not None:
            objs = self.can(u'view', u'event', definition=etype)
        else:
            objs = self.can(u'view', u'event')
            
        # add ApiViewResponse objects definition statically
        #objs[ApiViewResponse.objdef] = [u'*']
        
        try:
            count, events = self.event_manager.gets(oid=oid, etype=etype, 
                                                    data=data, source=source, 
                                                    dest=dest, datefrom=datefrom, 
                                                    dateto=dateto, page=page, 
                                                    size=size, objid=objid, 
                                                    objdef=objdef, 
                                                    objtype=objtype)
        except QueryError as ex:
            self.logger.error(ex, exc_info=1)
            raise ApiManagerError(ex)
        
        try:
            res = {u'events':[], 
                   u'count':size,
                   u'page':page,
                   u'total':count}
            for i in events:
                objdef = i.objdef.lower()
                if objdef not in objs:
                    continue
                
                # check authorization
                objset = set(objs[objdef])
                
                creation = str2uni(i.creation.strftime(u'%d-%m-%Y %H:%M:%S.%f'))
                data = None
                try:
                    data = json.loads(i.data)
                except  Exception as ex:
                    self.logger.warn(u'Can not parse event %s data' % i.id, exc_info=1)
                    
                obj = {u'id':i.id,
                       u'event_id':i.event_id,
                       u'type':i.type,
                       u'objid':i.objid,
                       u'objdef':i.objdef,
                       u'objtype':i.objtype,
                       u'date':creation,
                       u'data':data,
                       u'source':json.loads(i.source),
                       u'dest':json.loads(i.dest)}

                # create needs
                needs = self.get_needs(i.objid.split(u'//'))

                # check if needs overlaps perms
                if self.has_needs(needs, objset) is True:
                    res[u'events'].append(obj)
            
            self.logger.debug(u'Get events: %s' % truncate(res))
            return res
        except QueryError as ex:
            self.logger.error(ex)
            raise ApiManagerError(ex)
    '''

    @trace(entity=u'GenericEvent', op=u'types.view')
    def get_event_types(self):
        """Get event types.
      
        :return: List of event types
        :rtype: list
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """        
        # verify permissions
        self.check_authorization(GenericEvent.objtype, GenericEvent.objdef, 
                                 u'*', u'view')
        
        # get available event types
        try:
            res = set(self.event_manager.get_types())
        except QueryError, ex:
            self.logger.error(ex)
            raise ApiManagerError(ex)
        
        #res = event_types_available.intersection(event_types)
            
        self.logger.debug(u'Get event types: %s' % res)
        return res
    
    @trace(entity=u'GenericEvent', op=u'definitions.view')
    def get_entity_definitions(self):
        """Get event entity definition. 
      
        :return: List of entity definitions
        :rtype: list
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """        
        # verify permissions
        objs = self.can(u'view', u'event')
        event_types = set(objs.keys())
        
        # get available event types
        try:
            event_types_available = set(self.event_manager.get_entity_definitions())
        except QueryError, ex:
            self.logger.error(ex)
            raise ApiManagerError(ex)
        
        res = event_types_available.intersection(event_types)
        
        # add ApiViewResponse objects definition statically
        #res.append(ApiViewResponse.objdef)
            
        self.logger.debug(u'Get event entity definitions: %s' % res)
        return res
    
class GenericEvent(ApiObject):
    objtype = u'event'
    objdef = u'GenericEvent'
    objdesc = u'Generic Event'
    
class BaseEvent(object):
    def __init__(self, event):
        self.event = event
    
    def info(self):
        """
        """
        data = None
        try:
            data = json.loads(self.event.data)
        except  Exception as ex:
            self.logger.warn(u'Can not parse event %s data' % self.event.id)
                            
        obj = {u'id':self.event.id,
               u'event_id':self.event.event_id,
               u'type':self.event.type,
               u'objid':self.event.objid,
               u'objdef':self.event.objdef,
               u'objtype':self.event.objtype,
               u'date':format_date(self.event.creation),
               u'data':data,
               u'source':json.loads(self.event.source),
               u'dest':json.loads(self.event.dest)}        
        return obj
    
    def detail(self):
        """
        """
        return self.info()
       