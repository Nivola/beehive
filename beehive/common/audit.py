# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

import logging
import os

from beecell.logger.helper import ExtendedLogger
from elasticsearch import Elasticsearch
from datetime import datetime
from .data import operation
import pytz

# from typing import TYPE_CHECKING, Tuple

# if TYPE_CHECKING:
#     from beehive.common.apimanager import ApiController


logger = logging.getLogger(__name__)
logger.manager.setLoggerClass(ExtendedLogger)

# container connection
# try:
#     import gevent.local

#     container = gevent.local.local()  #: thread/gevent local container
# except Exception:
#     import threading

#     container = threading.local()

# container.connection = None

# beehive operation
try:
    import gevent.local

    CurrentLocal = gevent.local.local

except Exception:
    import threading

    CurrentLocal = threading.local


class Audit(CurrentLocal):
    initialized = False

    def __init__(
        self,
        state: int = 0,
        objid: str = "",
        objdef: str = "",
        api_method: str = "",
        request_id: str = "",
        req_method: str = "",
        subsystem: str = "",
        user: str = "",
        from_ip: str = "na",
        for_ip: str = "na",
    ):
        if self.initialized:
            logger.error("Audit __init__ called too many times")
            return
        self.initialized = True
        self.state = state
        self.objid = objid
        self.objdef = objdef
        self.api_method = api_method
        self.request_id = request_id
        self.req_method = req_method
        self.subsystem = subsystem
        self.user = user
        self.from_ip = from_ip
        self.for_ip = for_ip

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
            # if k in self.__dict__:
            #     self.__dict__[k] = v
        return self

    def set_objid(self, objdef: str, objid: str, force: bool = False):
        try:
            if objid is not None:
                if force:
                    self.objdef = objdef
                    self.objid = objid
                elif self.objid == "":
                    self.objdef = objdef
                    self.objid = objid
        except Exception as ex:
            logger.error(ex)
        return self

    def set_user(self, user: str = None):
        if user is None:
            if hasattr(operation, "user"):
                u = getattr(operation, "user")
                if hasattr(u, "__iter__") and len(u) >= 3:
                    self.user = u[0]
        else:
            self.user = user
        return self

    def send_audit(self, elastic: Elasticsearch, **kwargs):
        def now()->datetime:
            tz_local = pytz.timezone("Europe/Rome")
            p = datetime.now(tz_local)
            return p
            
        def currtimestamp(p: datetime) -> str:
            tz_utc = pytz.utc
            return p.astimezone(tz_utc).strftime("%Y-%m-%dT%H:%M:%S%z")


        api_env = os.getenv("API_ENV", "<superunknown>")
        # logger.debug("+++++ api_env: %s" % api_env)
        if api_env.startswith("lab"):
            logger.debug("send_audit ignored it is a lab")
            return
        if elastic is None:
            logger.warning("send_audit ignored elastic is NONE")
            return

        try:
            if self.user == "":
                if hasattr(operation, "user"):
                    u = getattr(operation, "user")
                    if hasattr(u, "__iter__") and len(u) >= 3:
                        self.user = u[0]
            dnow = now()
            item = {
                "http.request.id": self.request_id,
                "http.request.ip": self.from_ip,
                "http.request.for": self.for_ip,
                "url.path": self.api_method,
                "http.request.method": self.req_method,
                "input.type": self.subsystem,
                "user.name": self.user,
                "http.response.status_code": self.state,
                "service.target.id": self.objid,
                "service.target.type": self.objdef,
                "event.original": str(kwargs),
                "source.ip"  : self.from_ip,                
                "source.nat.ip": self.for_ip,
                "@timestamp": currtimestamp(dnow),
            }
            prefix = "cmp-audit-log"
            index = "%s-%s" % (prefix, dnow.date().strftime("%Y.%m.%d"))
            elastic.index(index=index, document=item)
            logger.debug("////////////////////send_audit////////////////////\n sent %s" % self)
        except Exception as ex:
            logger.error(ex)

    def __str__(self):
        return (
            "<Audit  initialized: %s, state: %s, objid: %s, objdef: %s, api_method: %s, request_id: %s, req_method: %s, subsystem: %s, user: %s >"
            % (
                self.initialized,
                self.state,
                self.objid,
                self.objdef,
                self.api_method,
                self.request_id,
                self.req_method,
                self.subsystem,
                self.user,
            )
        )


_localaudit: Audit = None


def initAudit(
    state: int = 0,
    objid: str = "",
    objdef: str = "",
    api_method: str = "",
    request_id: str = "",
    req_method: str = "",
    subsystem: str = "",
    user: str = "",
    from_ip="na",
    for_ip="na",
) -> Audit:
    logger.debug("////////////////////initAudit\\\\\\\\\\\\\\\\\\\\")
    global _localaudit
    _localaudit = Audit(
        state=state,
        objid=objid,
        objdef=objdef,
        api_method=api_method,
        request_id=request_id,
        req_method=req_method,
        subsystem=subsystem,
        user=user,
        from_ip=from_ip,
        for_ip=for_ip,
    )
    return _localaudit


def localAudit() -> Audit:
    global _localaudit
    if _localaudit is None:
        logger.error("localAudit is none")
        _localaudit = Audit(
            state=0, objid="", objdef="", api_method="", request_id=operation.id, req_method="", subsystem="", user=""
        )
    logger.debug("localAudit: %s " % _localaudit)
    return _localaudit
