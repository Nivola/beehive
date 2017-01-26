'''
Created on Aug 13, 2014

@author: darkbk
'''
import ujson as json
from flask import request
from datetime import datetime
from beehive.common.apimanager import ApiManagerError, ApiView

class GetEvents(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        # filter string can be type+data+source+datefrom+dateto
        # - type : '' or '<event type>'
        # - data : '' or '<event data>'
        # - source : '' or '<event source>'
        # - datefrom : '' or '2015-3-9-15-23-56'
        # - dateto : '' or '2015-3-9-15-23-56'
        event_type = request.args.get('type', None)
        event_data = request.args.get('data', None)
        source = request.args.get('source', None)
        datefrom = request.args.get('datefrom', None)
        dateto = request.args.get('dateto', None)
        page = request.args.get('page', 0)
        size = request.args.get('size', 10)
        objid = request.args.get('objid', None)
        objdef = request.args.get('objdef', None)
        objtype = request.args.get('objtype', None)

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
        return resp

class GetEvent(ApiView):
    def dispatch(self, controller, data, oid, *args, **kwargs):    
        events = controller.get_events(oid=oid)
        if events[u'total'] == 0:
            raise ApiManagerError('Event %s does not exists' % oid)
        return events[u'rows'][0]

class EventAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            ('events', 'GET', GetEvents, {}),
            ('event/types', 'GET', GetEventTypes, {}),
            ('event/<oid>', 'GET', GetEvent, {}),
        ]

        ApiView.register_api(module, rules)
