'''
Created on Nov 3, 2017

@author: io
'''
from cement.ext.ext_argparse import ArgparseArgumentHandler as Handler
from argparse import ArgumentParser

class ArgparseArgumentHandler(Handler):
    def __init__(self, *args, **kw):
        super(ArgumentParser, self).__init__(add_help=False, *args, **kw)
        super(Handler, self).__init__(*args, **kw)
        self.config = None
        self.unknown_args = None
        self.parsed_args = None

def load(app):
    app.handler.register(ArgparseArgumentHandler)