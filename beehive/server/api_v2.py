# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

import gevent.monkey

gevent.monkey.patch_all()

from beehive.common.flask_app_v2 import BeehiveAppV2

################################################################################
# app section
################################################################################
# Create app
app = BeehiveAppV2(__name__)
