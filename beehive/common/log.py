# SPDX-License-Identifier: GPL-3.0-or-later
#
# (C) Copyright 2018-2019 CSI-Piemonte

from celery.utils.log import ColorFormatter as CeleryColorFormatter
from celery.utils.term import colored


class ColorFormatter(CeleryColorFormatter):
    #: Loglevel -> Color mapping.
    COLORS = colored().names
    colors = {u'DEBUG': COLORS[u'blue'], 
              u'WARNING': COLORS[u'yellow'],
              u'WARN': COLORS[u'yellow'],
              u'ERROR': COLORS[u'red'], 
              u'CRITICAL': COLORS[u'magenta']}
