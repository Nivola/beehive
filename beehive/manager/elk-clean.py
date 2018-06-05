#!/usr/bin/python
# -*- coding: utf-8 -*-
'''

@Created on Mag 03, 2018
@author: Gianpiero Ardissono
@cosa_fa: Questo script gestisce lo svecchiamento degli indici presenti in ElasticSearch
        Lo svecchiamento è impostato in 90 giorni
@motto: Siamo i 'sultans of cloud': quello che c'e' lo usiamo, quello che non c'e' lo creiamo
@Progetto:
@Parametri in ingresso: pod (podto1, podto2, podvc)
@Parametri di configurazione presenti nel codice --> indici_da_tenere = 90

'''

import re, sys
import requests

indici_da_tenere = 90
list_ind = []
lista_indici = []
temp_list = []
sorted_list_onlybeat = []

ar = sys.argv
if len(ar)!=2: pod="podto1"
else: pod = ar[1]

if pod in ["podto1","podto2","podvc"]:
    if pod == "podto1":
        url = 'http://10.138.144.85:9200/_cat/indices'
        url_del = 'http://10.138.144.85:9200/'
    elif pod == "podto2":
        url = 'http://10.138.176.85:9200/_cat/indices'
        url_del = 'http://10.138.176.85:9200/'
    elif pod == "podvc":
        url = 'http://10.138.208.85:9200/_cat/indices'
        url_del = 'http://10.138.208.85:9200/'

#        res = requests.get(url, data="")
res = requests.get(url)

for riga in res.text.split("\n"):
    list_ind = re.findall(r'\S+',riga)
    if len(list_ind) == 10:
        diz_indici = {u"healt": list_ind[0],
                      u"status": list_ind[1],
                      u"indice": list_ind[2],
                      u"uuid": list_ind[3],
                      u"pri":list_ind[4],
                      u"rep":list_ind[5],
                      u"doccount": list_ind[6],
                      u"docdeleted": list_ind[7],
                      u"storesize": list_ind[8],
                      u"pristoresize": list_ind[9]}
        lista_indici.append(diz_indici)
#  print lista_indici
key_list = ("indice","healt","status","uuid","pri","rep","doccount","docdeleted","storesize","pristoresize")

for i in lista_indici:
       temp_list.append(sorted(i.items(),key=lambda pair: key_list.index(pair[0])))
sorted_list=sorted(temp_list)

for i in sorted_list:
    if "filebeat" in i[0][1]:
        sorted_list_onlybeat.append(i)
'''
for i in sorted_list_onlybeat:
    print i
'''
quanti_totale = len(sorted_list_onlybeat)
print "ci sono: " + str(quanti_totale) + " indici."

c = quanti_totale
for i in sorted_list_onlybeat:
    c = c - 1
    if c < indici_da_tenere:
        continue
    else:
        indice = i[0][1]
        url_canc=url_del + indice
        res = requests.delete(url_canc)
        if res.status_code==200:
            print "L'indice "+ indice + " del pod "+ pod + " e' stato cancellato!!"
        else:
            print "L'indice "+ indice + " del pod "+ pod + " non e' stato trovato!!"