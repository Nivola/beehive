'''
Created on Dec 31, 2014

@author: darkbk
'''
from beecell.perf import watch
from beecell.simple import str2uni, id_gen, truncate
import ujson as json
from beehive.common.apimanager import ApiController, ApiManagerError,\
    ApiViewResponse
from beehive.module.event.model import EventDbManager
from beecell.db import QueryError

class EventController(ApiController):
    """Event Module controller.
    """    
    version = u'v1.0'
    
    def __init__(self, module):
        ApiController.__init__(self, module)

        self.event_manager = EventDbManager()
                
    def init_object(self):
        """Register object types, objects and permissions related to module.
        Call this function when initialize system first time.
        """
        pass
    
    @watch
    def get_events(self, oid=None, etype=None, data=None, 
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
                # check authorization
                objset = set(objs[i.objdef.lower()])
                
                creation = str2uni(i.creation.strftime("%d-%m-%y %H:%M:%S"))
                data = None
                try:
                    data = json.loads(i.data)
                except  Exception as ex:
                    self.logger.warn("Can not parse event data")
                    
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

    @watch
    def get_event_types(self):
        """Get event types.
      
        :return: List of event types
        :rtype: list
        :raises ApiManagerError: raise :class:`ApiManagerError`
        """        
        # verify permissions
        #objs = self.can(u'view', u'event')
        #event_types = set(objs.keys())
        
        # get available event types
        try:
            res = set(self.event_manager.get_types())
        except QueryError, ex:
            self.logger.error(ex)
            raise ApiManagerError(ex)
        
        #res = event_types_available.intersection(event_types)
            
        self.logger.debug(u'Get event types: %s' % res)
        return res
    
    @watch
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