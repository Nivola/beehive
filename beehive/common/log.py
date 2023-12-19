# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from celery.utils.log import ColorFormatter as CeleryColorFormatter
from celery.utils.term import colored


class ColorFormatter(CeleryColorFormatter):
    #: Loglevel -> Color mapping.
    COLORS = colored().names
    colors = {
        "DEBUG": COLORS["blue"],
        "WARNING": COLORS["yellow"],
        "WARN": COLORS["yellow"],
        "ERROR": COLORS["red"],
        "CRITICAL": COLORS["magenta"],
    }
