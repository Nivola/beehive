'''
Created on Dec 31, 2014

@author: darkbk
'''
from beehive.common.data import TransactionError, QueryError
#from .model import ConfigDbManagerError, ConfigDbManager
from beecell.perf import watch
from beehive.common.apimanager import ApiController, ApiManagerError, ApiObject
from beehive.module.event.model import EventDbManager
from beecell.simple import str2uni, id_gen, truncate
import ujson as json

class EventController(ApiController):
    """Event Module controller.
    """    
    version = 'v1.0'    
    
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
        :param datefrom: event data from [optional]
        :param dateto: event data to [optional]
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
            objs = self.can('view', 'event', definition=etype)
        else:
            objs = self.can('view', 'event')
        
        #event_types = objs.keys()
        
        try:
            count, events = self.event_manager.gets(oid=oid, etype=etype, 
                                                    data=data, source=source, 
                                                    dest=dest, datefrom=datefrom, 
                                                    dateto=dateto, page=page, 
                                                    size=size, objid=objid, 
                                                    objdef=objdef, 
                                                    objtype=objtype)
        except QueryError, ex:
            self.logger.error(ex)
            raise ApiManagerError(ex)
        
        try:
            res = {u'rows':[], u'total':count}
            for i in events:
                # check authorization
                objset = set(objs[i.objdef])
                
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
                needs = self.get_needs(i.objid.split('//'))
                
                # check if needs overlaps perms
                if self.has_needs(needs, objset) is True:
                    res[u'rows'].append(obj)
            
            self.logger.debug('Get events: %s' % truncate(res))
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
        objs = self.can('view', 'event')
        event_types = set(objs.keys())
        
        # get available event types
        try:
            event_types_available = set(self.event_manager.get_types())
        except QueryError, ex:
            self.logger.error(ex)
            raise ApiManagerError(ex)
        
        res = event_types_available.intersection(event_types)
            
        self.logger.debug('Get event types: %s' % res)
        return res