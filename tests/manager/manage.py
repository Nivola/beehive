'''
Created on Jan 11, 2017

@author: darkbk
'''
# test
./manage.py test redis 10.102.160.240
./manage.py test mysql 10.102.160.240 resource resource resource
./manage.py test beehive 10.102.184.52 6060

# init subsystem
./manage.py init auth auth.json
./manage.py init auth auth.json resource.json