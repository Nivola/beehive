# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import gevent.monkey

gevent.monkey.patch_all()

from beehive.common.flask_app import BeehiveApp

################################################################################
# app section
################################################################################
# Create app
app = BeehiveApp(__name__)
