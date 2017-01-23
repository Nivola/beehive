#!/usr/bin/env python

'''
Created on Nov 25, 2013

@author: darkbk
'''
import sys
import os
from beecell.server.uwsgi_server.console import main

if __name__ == '__main__':
    run_path = os.path.dirname(os.path.realpath(__file__))
    retcode = main(run_path, sys.argv[1:])
    sys.exit(retcode)