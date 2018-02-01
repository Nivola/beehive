"""
Created on Nov 20, 2017

@author: darkbk
"""
import logging
from cement.core.controller import expose
from beehive.manager.util.controller import BaseController, ApiController
from re import match
from beecell.simple import truncate

logger = logging.getLogger(__name__)


class BusinessController(BaseController):
    class Meta:
        label = 'business'
        stacked_on = 'base'
        stacked_type = 'nested'
        description = "Business Service and Authority Management"
        arguments = []

    def _setup(self, base_app):
        BaseController._setup(self, base_app)


business_controller_handlers = [
    BusinessController
]