# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte


class BeehiveApiClientAuthority(object):
    """Beehive api client for service authority module"""

    def __init__(self, client):
        self.c = client

    def instance_exist(self, type, name):
        """Check service instance with this name exists"""
        uri = "/v1.0/nws/serviceinsts"
        res = self.c.cmp_get(uri, data="name=%s" % name)
        self.logger.info("Get service instance by name: %s" % res)
        count = res.get("count")
        if count > 0:
            self.c.output("Service %s %s already exists" % (type, name))
            return True

        return False
