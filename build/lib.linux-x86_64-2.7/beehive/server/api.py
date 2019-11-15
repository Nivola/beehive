# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

import os
#os.environ['GEVENT_RESOLVER'] = 'ares'
#os.environ['GEVENTARES_SERVERS'] = 'ares'

#import beecell.server.gevent_ssl
import gevent.monkey
# apply monkey patch
gevent.monkey.patch_all()
# apply monkey patch to psycopg2
# from psycogreen.gevent import patch_psycopg
# patch_psycopg()

from beehive.common.flask_app import BeehiveApp

################################################################################
# app section
################################################################################
# Create app
app = BeehiveApp(__name__)