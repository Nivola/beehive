# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte
# (C) Copyright 2019-2020 CSI-Piemonte

import gevent.monkey

gevent.monkey.patch_all()

from beehive.common.flask_app import BeehiveApp

################################################################################
# app section
################################################################################
# Create app
app = BeehiveApp(__name__)
