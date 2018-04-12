'''
Created on Aug 30, 2016

@author: io
'''
import logging
from flask import Flask
from gibbonportal2.util.cloudapi import CloudapiClient
from beecell.logger.helper import LoggerHelper
from beecell.flask.render import render_template
from beedrones.vsphere.client import VsphereManager

app = Flask(__name__)

vcenter = {'host':'172.25.3.10', 'port':443, 
           'user':'administrator@nuvolacsi.local', 
           'pwd':'Vcenterlab$2016', 'verified':False}
nsx = None

util = VsphereManager(vcenter, nsx)
server = util.server.get_by_morid('vm-83')
info = util.server.remote_console(server, to_vcenter=True)

@app.route('/')
def get_console():
    proto = 'http'
    host = '10.102.160.12'
    port = 6062
    timeout = 5
    
    user = 'admin'
    password = 'testlab'
    login_ip = 'localhost'
    
    auth = CloudapiClient(proto, host, 6060, timeout)
    client = CloudapiClient(proto, host, port, timeout)
    uid, seckey, user, ru = auth.login(user, password, login_ip)
    
    # get vm console
    baseuri = '/v1.0/resource/vsphere'
    contid = 14
    oid = 1047
    path = u'%s/%s/server/%s/console/' % (baseuri, contid, oid)
    method = u'GET'
    res = client.send_signed_api_request(path, method, uid, seckey, '')
    
    return render_template('console.html', uri=res[u'uri'])

@app.route('/cons')
def get_console2():
    print info['uri']
    return render_template('console2.html', uri=info['uri'])

logger = logging.getLogger('gibbonportal2')
LoggerHelper.setup_simple_handler(logger, logging.DEBUG)
logger = logging.getLogger('beecell')
LoggerHelper.setup_simple_handler(logger, logging.DEBUG)

app.run(host='localhost', port=8000, debug=True)