'''
Created on Aug 13, 2014

@author: darkbk
'''
import ujson as json
from flask import request
from datetime import datetime
from beehive.common.apimanager import ApiView, ApiManagerError

class GetEvents(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        # filter string can be type+data+source+datefrom+dateto
        # - type : '' or '<event type>'
        # - data : '' or '<event data>'
        # - source : '' or '<event source>'
        # - datefrom : '' or '2015-3-9-15-23-56'
        # - dateto : '' or '2015-3-9-15-23-56'
        event_type = request.args.get(u'type', None)
        event_data = request.args.get(u'data', None)
        source = request.args.get(u'source', None)
        datefrom = request.args.get(u'datefrom', None)
        dateto = request.args.get(u'dateto', None)
        page = request.args.get(u'page', 0)
        size = request.args.get(u'size', 10)
        objid = request.args.get(u'objid', None)
        objdef = request.args.get(u'objdef', None)
        objtype = request.args.get(u'objtype', None)

        try: datefrom = datetime.strptime(datefrom, "%d-%m-%y-%H-%M-%S")
        except: datefrom = None
        
        try: dateto = datetime.strptime(dateto, "%d-%m-%y-%H-%M-%S")
        except: dateto = None
        
        #self.logger.debug("filter: type=%s, data=%s, source=%s, datefrom=%s, dateto=%s" % (
        #                   get_field(0), get_field(1), get_field(2),
        #                   datefrom, dateto))
        
        resp = controller.get_events(etype=event_type, data=event_data, 
                                     source=source, datefrom=datefrom, 
                                     dateto=dateto, page=int(page), 
                                     size=int(size), objid=objid, 
                                     objdef=objdef, objtype=objtype)
        return resp

class GetEventTypes(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        resp = controller.get_event_types()
        return {u'event-types':resp,
                u'count':len(resp)}
        
class GetEventEntityDefinition(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        resp = controller.get_entity_definitions()
        return {u'event-entities':resp,
                u'count':len(resp)}        

class GetEvent(ApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):    
        events = controller.get_events(oid=oid)
        if events[u'count'] == 0:
            raise ApiManagerError(u'Event %s does not exists' % oid)
        return {u'event':events[u'events'][0]}

class EventAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            (u'events', u'GET', GetEvents, {}),
            (u'events/types', u'GET', GetEventTypes, {}),
            (u'events/entities', u'GET', GetEventEntityDefinition, {}),
            (u'events/<oid>', u'GET', GetEvent, {}),
        ]

        ApiView.register_api(module, rules)
