"""
Created on Jan 18, 2018

@author: darkbk

passi principali:
- creo un modulo in sections
- creo un controller nested in base -> ExampleController
- creo una lista dove inserisco progressivamente tutti i controller -> example_controller_handlers
- aggiunto la lista dei controller alla app manager -> file manage.py riga 197

- per ogni nuovo controller ....
"""
import requests
import sh
import logging
from cement.core.controller import expose
from gevent import sleep

from beehive.manager.util.controller import BaseController, ApiController,\
    check_error
from re import match
from beecell.simple import truncate, id_gen
from beedrones.openstack.client import OpenstackManager
from beehive.manager.sections.resource import ResourceEntityController
from paramiko.client import SSHClient, MissingHostKeyPolicy

logger = logging.getLogger(__name__)


class ExampleController(BaseController):
    class Meta:
        label = 'example'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Example section tree"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)


example_controller_handlers = [
    ExampleController,
]