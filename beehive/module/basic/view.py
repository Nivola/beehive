'''
Created on Apr 01, 2016

@author: darkbk
'''
from beehive.common.apimanager import ApiView

class ServerPing(ApiView):
    def get(self, controller, data, *args, **kwargs):
        """
        Server ping api
        Call this api to ping server
        ---
        tags:
          - Basic server api      
        produces:
          - application/json
          - application/xml
        responses:
          500:
            $ref: "#/responses/InternalServerError"
          400:
            $ref: "#/responses/BadRequest"
          401:
            $ref: "#/responses/Unauthorized"
          403:
            $ref: "#/responses/Forbidden"
          404:
            $ref: "#/responses/NotFound"
          405:
            $ref: "#/responses/MethodAotAllowed" 
          408:
            $ref: "#/responses/Timeout"
          410:
            $ref: "#/responses/Gone"            
          415:
            $ref: "#/responses/UnsupportedMediaType"
          422:
            $ref: "#/responses/UnprocessableEntity"
          429:
            $ref: "#/responses/TooManyRequests"           
          default: 
            $ref: "#/responses/Default"          
          200:
            description: Ping response
            schema:
              type: object
              properties:
                name:
                  type: string
                  example: beehive
                id:
                  type: string
                  example: auth-01
        """
        resp = controller.ping()
        return resp

class ServerInfo(ApiView):
    def get(self, controller, data, *args, **kwargs):
        """

        """  
        resp = controller.info()
        return resp

class ServerProcessTree(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        """
        bla bla
        ---
        """        
        resp = controller.processes()
        return resp
    
class ServerWorkers(ApiView):
    def get(self, controller, data, *args, **kwargs):
        """

        """        
        resp = controller.workers()
        return resp

class ServerConfigs(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        """
        bla bla
        ---
        """        
        resp = controller.get_configs()
        return resp

class ServerUwsgiConfigs(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        """
        bla bla
        ---
        """        
        resp = controller.get_uwsgi_configs()
        return resp
    
class ServerReload(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        """
        bla bla
        ---
        """        
        resp = controller.reload()
        return resp

#
# flask inspection
#
class ServerFlaskSessions(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        """
        bla bla
        ---
        """        
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
        """
        bla bla
        ---
        """        
        res = controller.database_ping()
        return res

class ListDatabaseTables(ApiView):
    def dispatch(self, controller, data, *args, **kwargs):
        """
        bla bla
        ---
        """        
        res = controller.database_tables()
        return res
    
class GetDatabaseTable(ApiView):
    def dispatch(self, controller, data, table, *args, **kwargs):
        """
        bla bla
        ---
        """        
        res = controller.database_query(table_name=table, 
                                     where=None, fields='*', 
                                     rows=100, offset=0)
        return res
    
class GetDatabaseTableRecord(ApiView):
    def dispatch(self, controller, data, table, row, offset, *args, **kwargs):
        """
        bla bla
        ---
        """        
        res = controller.database_query(table_name=table, 
                                     where=None, fields='*', 
                                     rows=int(row), 
                                     offset=int(offset))        
        return res    
    
class GetDatabaseTableRecordCount(ApiView):
    def dispatch(self, controller, data, table, *args, **kwargs):
        """
        bla bla
        ---
        """
        res = controller.database_count(table_name=table, where=None)        
        return res
    
class GetDatabaseTableRecordDesc(ApiView):
    def dispatch(self, controller, data, table, *args, **kwargs):
        """
        bla bla
        ---
        tags:
          - users
        parameters:
          - name: team_id
            in: path
            description: ID of team (type any number)
            required: true
            type: int32
        definitions:
          User:
            type: object
            properties:
              name:
                type: string
              team:
                type: int32
        responses:
          200:
            description: Returns a list of users
            schema:
              id: Users
              type: object
              properties:
                users:
                  type: array
                  items:
                    $ref: '#/definitions/User'
            examples:
              users: [{'name': 'Russel Allen', 'team': 66}]        
        """
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
            (u'server/workers', u'GET', ServerWorkers, {u'secure':False}),
            (u'server/configs', u'GET', ServerConfigs, {}),
            (u'server/uwsgi/configs', u'GET', ServerUwsgiConfigs, {}),          
            (u'server/reload', u'PUT', ServerReload, {}),
            
            (u'server/sessions', u'GET', ServerFlaskSessions, {}),
            
            
            #(u'server/db/ping', u'GET', PingDatabase, {}),
            #(u'server/db/tables', u'GET', ListDatabaseTables, {}),
            #(u'server/db/table/<table>', u'GET', GetDatabaseTable, {}),
            #(u'server/db/table/<table>/<row>/<offset>', u'GET', GetDatabaseTableRecord, {}),
            #(u'server/db/table/<table>/count', u'GET', GetDatabaseTableRecordCount, {}),
            #(u'server/db/table/<table>/desc', u'GET', GetDatabaseTableRecordDesc, {})
        ]

        ApiView.register_api(module, rules)