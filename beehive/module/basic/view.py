'''
Created on Apr 01, 2016

@author: darkbk
'''
from beehive.common.apimanager import ApiView


class ServerPing(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        resp = controller.ping()
        return resp

class ServerInfo(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        resp = controller.info()
        return resp

class ServerProcessTree(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        resp = controller.processes()
        return resp
    
class ServerWorkers(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        resp = controller.workers()
        return resp

class ServerConfigs(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        resp = controller.get_configs()
        return resp

class ServerUwsgiConfigs(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        resp = controller.get_uwsgi_configs()
        return resp
    
class ServerReload(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):    
        resp = controller.reload()
        return resp

#
# flask inspection
#
class ServerFlaskSessions(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):   
        app = controller.module.api_manager.app
        res = app.session_interface.list_sessions()
        resp = {u'sessions':res,
                u'count':len(res)}
        return resp

#
# database api
#
class PingDatabase(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        res = controller.database_ping()
        return res

class ListDatabaseTables(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        res = controller.database_tables()
        return res
    
class GetDatabaseTable(ApiView):
    def dispatch(self, controller, data, table, *args, **kwargs):
        res = controller.database_query(table_name=table, 
                                     where=None, fields='*', 
                                     rows=100, offset=0)
        return res
    
class GetDatabaseTableRecord(ApiView):
    def dispatch(self, controller, data, table, row, offset, *args, **kwargs):
        res = controller.database_query(table_name=table, 
                                     where=None, fields='*', 
                                     rows=int(row), 
                                     offset=int(offset))        
        return res    
    
class GetDatabaseTableRecordCount(ApiView):
    def dispatch(self, controller, data, table, *args, **kwargs):
        res = controller.database_count(table_name=table, where=None)        
        return res
    
class GetDatabaseTableRecordDesc(ApiView):
    def dispatch(self, controller, data, table, *args, **kwargs):
        res = controller.database_table_desc(table)
        return res

class BaseAPI(ApiView):
    """
    """
    @staticmethod
    def register_api(module):
        rules = [
            (u'server/ping', u'GET', ServerPing, {u'secure':False}),
            (u'server', u'GET', ServerInfo, {u'secure':False}),
            (u'server/processes', u'GET', ServerProcessTree, {}),
            (u'server/workers', u'GET', ServerWorkers, {}),
            (u'server/configs', u'GET', ServerConfigs, {}),
            (u'server/uwsgi/configs', u'GET', ServerUwsgiConfigs, {}),          
            (u'server/reload', u'PUT', ServerReload, {}),
            
            (u'server/sessions', u'GET', ServerFlaskSessions, {}),
            
            (u'server/db/ping', u'GET', PingDatabase, {}),
            (u'server/db/tables', u'GET', ListDatabaseTables, {}),
            (u'server/db/table/<table>', u'GET', GetDatabaseTable, {}),
            (u'server/db/table/<table>/<row>/<offset>', u'GET', GetDatabaseTableRecord, {}),
            (u'server/db/table/<table>/count', u'GET', GetDatabaseTableRecordCount, {}),
            (u'server/db/table/<table>/desc', u'GET', GetDatabaseTableRecordDesc, {})
        ]

        ApiView.register_api(module, rules)