"""
Created on Dec 20, 2017

@author: darkbk
"""
import logging
from time import sleep
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController,\
    check_error
from re import match
from beecell.simple import truncate
from beedrones.vsphere.client import VsphereManager
from beecell.remote import RemoteClient

# get graphite data
from pylab import plot,hist, show, title, text, xlabel, ylabel
from scipy import stats
import time
import os
import sys
import requests
import yaml
import numpy as np
import json
from texttable import Texttable

logger = logging.getLogger(__name__)


# get data from graphite


def getdata_from_graphite(ip_address_graphite_f,pod_f,vm_f,metrics_f,function_f,period_f,ask_what_kind_of_question_f):

    ip_address_graphite = ip_address_graphite_f
    pod = pod_f
    vm = vm_f
    metrics = metrics_f
    function = function_f
    period = period_f
    tipodato = "json"
    ask_what_kind_of_question = ask_what_kind_of_question_f

    grafico = False

    #print("1 ip_address_graphite: ",ip_address_graphite)
    #print("2 pod :",pod)
    #print("3 vm :",vm)
    #print("4 metrics :",metrics)
    #print("5 function :",function)
    #print("6 period :",period)
    #print("7 tipodato :",tipodato)

    #os.system("set http_proxy")
    #sys.exit()

    #string_query = "http://"+ip_address_graphite+"/render/?target="+pod+"."+vm+"."+metrics+"."+function+"&from"+period+"&format"+tipodato
    if (ask_what_kind_of_question_f == "coarse"):
        string_query = "http://"+ip_address_graphite+"/render?target="+pod+"."+vm+"."+metrics+"."+function+"&from=-"+period+"&format="+tipodato
    elif (ask_what_kind_of_question_f == "highestMax"):
        string_query = "http://"+ip_address_graphite+"/render?target="+"highestMax("+pod+"."+"*"+"."+metrics+"."+"percentage"+",10)"+"&from=-"+period+"&format="+tipodato
    elif (ask_what_kind_of_question_f == "one"):
        string_query = "http://"+ip_address_graphite+"/render?target="+pod+"."+vm+"."+metrics+"."+function+"&from=-"+period+"&format="+tipodato


    #print ("string_query|%s|" % string_query)

    content = requests.get(string_query)

    #content = requests.get("http://10.102.184.96/render/?target=averageSeries(test.kvm.instance-*.memory.percentage)&from=-1hour&format=json")
    #content = requests.get("http://10.102.184.96/render/?target=pod-vm.metrics.percentage&from=-1day&format=json")


    #print("\nStatus_Code :|%s|" % content.status_code)

    stringa_get = content.text
    #print("stringa_get:",stringa_get)
    len_stringa = len(stringa_get)
    stringa_get = stringa_get[1:(len_stringa-1)]
    #print("stringa_get", stringa_get)
    #print("stringa_get:",stringa_get)
    dict_get = yaml.load(stringa_get)


    target = dict_get['target']
    #print("target|",target)
    #print ("\ntarget: %s" % (target))
    stringa_datapoints = dict_get['datapoints']

    #print ("datapoins|",stringa_datapoints)

    i=0
    metrica = []
    array_x = []
    array_y = []

    lenmenouno = (len(stringa_datapoints)-1)

    while i <= lenmenouno:
        metrica = stringa_datapoints[i]
        metrica_valore = metrica[0]
        metrica_tempo = metrica[1]
        if (i == 0):
            inizio_tempo = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(metrica_tempo))
            #print("Inizio periodo: ",inizio_tempo)

        if (i == (lenmenouno)):
            fine_tempo = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(metrica_tempo))
            #print("Fine periodo: ",fine_tempo)
        media = 0
        tot_value = 0
        if ((metrica[0]) or (metrica[0]==0)):
            array_x.insert(i, metrica_tempo)
            array_y.insert(i, metrica_valore)

        i = i + 1

    if(ask_what_kind_of_question_f == "one"):
        if (len(array_y)!=0):
            #facciamo la somma di ogni valore
            #print("array_y",array_y)
            k = 0
            for z in range (len(array_y)):

            #print(array_y[z][0])
                tot_value += array_y[k]
                k = k+1
                media = tot_value / k
        if(media >=0):
            print (media)
        return


    tab1 = Texttable()

    header = ['Inizio', 'Fine', 'Target']
    tab1.header(header)
    tab1.set_cols_width([30,30,55])
    row = [inizio_tempo, fine_tempo, target]
    tab1.add_row(row)
    print tab1.draw()

    # print as graph
    if grafico == True:

        x = np.array(array_x)
        y = np.array(array_y)
        plot(x,y,'ro')

        titolo_plot = "%s\nfrom %s to %s\n" % (target,inizio_tempo,fine_tempo)
        print (titolo_plot)
        title (titolo_plot)
        xlabel ('Seconds')
        ylabel ('Value Metrics')
        show()

    # print as table

    stringa_json  = json.loads(stringa_get)
    #print (type(stringa_json))

    #print (json.dumps(stringa_json, indent=2))
    #print ("Valore target: ", stringa_json['target'])
    #print ("Misure: ", stringa_json['datapoints'])

    #print ("Numero valori:",(len(stringa_json['datapoints'])))
    num_val = (len(stringa_json['datapoints']))

    tab2 = Texttable()

    i = 0
    header=("Value","Time")
    tab2.header(header)
    tab2.set_cols_align(['r','r'])

    while(i < num_val):
        #print(stringa_json['datapoints'][i])
        tab2.add_row(stringa_json['datapoints'][i])
        i = i+1

    print tab2.draw()

#
# graphite native platform
#
class GraphitePlatformController(BaseController):
    class Meta:
        label = 'graphite.platform'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Graphite Platform management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)

class SecondController(BaseController):
    class Meta:
        label = 'metrics'
        stacked_on = 'graphite.platform'
        stacked_type = 'nested'
        description = "this is the second controller (stacked/nested on base)"
        arguments = [
            (['--2nd-opt'], dict(help="another option under base controller")),
                (['extra_arguments'],
                 dict(action='store', nargs='*')),
            ]

    @expose(help="metrics default command", hide=True)
    def default(self):
        print "Inside SecondController.default()"

    @expose(help="this is a command under the second-controller namespace")
    def vm(self):
        print "Inside SecondController.vm()"

        if (self.app.pargs.extra_arguments) and (len(self.app.pargs.extra_arguments)==6):
            print "%s" % self.app.pargs.extra_arguments[0]
            print "%s" % self.app.pargs.extra_arguments[1]
            print "%s" % self.app.pargs.extra_arguments[2]
            print "%s" % self.app.pargs.extra_arguments[3]
            print "%s" % self.app.pargs.extra_arguments[4]
            print "%s" % self.app.pargs.extra_arguments[5]

            ip_address_graphite_b = self.app.pargs.extra_arguments[0]
            pod_b = self.app.pargs.extra_arguments[1]
            vm_b = self.app.pargs.extra_arguments[2]
            metrics_b = self.app.pargs.extra_arguments[3]
            function_b = self.app.pargs.extra_arguments[4]
            period_b = self.app.pargs.extra_arguments[5]
            ask_what_kind_of_question_b = "coarse"

            # getdata_from_graphite("10.138.144.75","podto1.kvm","instance-00000010","disk.0","percentage","-30min")
            getdata_from_graphite(ip_address_graphite_b, pod_b, vm_b, metrics_b, function_b, period_b, ask_what_kind_of_question_b)
        else:
            print("check arguments!")

class ThirdController(BaseController):
    class Meta:
        label = 'highest'
        stacked_on = 'graphite.platform'
        stacked_type = 'nested'
        description = "this controller is nested in the graphite.platform"
        arguments = [
            (['--3rd-opt'], dict(help="an option only under 3rd controller")),
            (['extra_arguments'],
             dict(action='store', nargs='*')),
            ]

    @expose(help="domain default command", hide=True)
    def default(self):
        print "Inside ThirdController.default()"

    @expose(help="this is a command under the second-controller namespace")
    def vm(self):
        print "Inside ThirdController.vm()"

        if (self.app.pargs.extra_arguments) and (len(self.app.pargs.extra_arguments)==5):
            print "highestMax"
            print "%s" % self.app.pargs.extra_arguments[0]
            print "%s" % self.app.pargs.extra_arguments[1]
            print "*"
            print "%s" % self.app.pargs.extra_arguments[2]
            print "%s" % self.app.pargs.extra_arguments[3]
            print "%s" % self.app.pargs.extra_arguments[4]

            ip_address_graphite_b = self.app.pargs.extra_arguments[0]
            pod_b = self.app.pargs.extra_arguments[1]
            vm_b = "*"
            metrics_b = self.app.pargs.extra_arguments[2]
            function_b = self.app.pargs.extra_arguments[3]
            period_b = self.app.pargs.extra_arguments[4]
            ask_what_kind_of_question_b = "highestMax"

            # getdata_from_graphite("10.138.144.75","podto1.kvm","instance-00000010","disk.0","percentage","-30min")
            getdata_from_graphite(ip_address_graphite_b, pod_b, vm_b, metrics_b, function_b, period_b, ask_what_kind_of_question_b)
        else:
            print("check arguments!")


class FourthController(BaseController):
    class Meta:
        label = 'one'
        stacked_on = 'graphite.platform'
        stacked_type = 'nested'
        description = "this controller is nested on the graphite.platform"
        arguments = [
            (['--4rd-opt'], dict(help="one vm ip_address_graphite pod.infrastructure instance metrics type period. Example:one vm 10.138.144.75 podto1.kvm instance-00000010 memory percentage 15min")),
            (['extra_arguments'],
             dict(action='store', nargs='*')),
            ]

    @expose(help="a command only under the fourth-controller namespace")
    def default(self):
        #print "Inside FourthController.default()"
        pass


    @expose(help="this is a command under the second-controller namespace")
    def vm(self):
        #print "Inside FourthController.pod()"

        if (self.app.pargs.extra_arguments) and (len(self.app.pargs.extra_arguments)==6):
            #print "%s" % self.app.pargs.extra_arguments[0]
            #print "%s" % self.app.pargs.extra_arguments[1]
            #print "%s" % self.app.pargs.extra_arguments[2]
            #print "%s" % self.app.pargs.extra_arguments[3]
            #print "%s" % self.app.pargs.extra_arguments[4]
            #print "%s" % self.app.pargs.extra_arguments[5]

            ip_address_graphite_b = self.app.pargs.extra_arguments[0]
            pod_b = self.app.pargs.extra_arguments[1]
            vm_b = self.app.pargs.extra_arguments[2]
            metrics_b = self.app.pargs.extra_arguments[3]
            function_b = self.app.pargs.extra_arguments[4]
            period_b = self.app.pargs.extra_arguments[5]
            ask_what_kind_of_question_b = "one"

            # getdata_from_graphite("10.138.144.75","podto1.kvm","instance-00000010","disk.0","percentage","-30min")
            getdata_from_graphite(ip_address_graphite_b, pod_b, vm_b, metrics_b, function_b, period_b, ask_what_kind_of_question_b)
        else:
            print("check arguments!")


graphite_controller_handlers = [
    GraphitePlatformController,
    SecondController,
    ThirdController,
    FourthController,
]
