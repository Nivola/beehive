#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

"""
Usage: catalog.py config_file

Options:
  -h, --help               Print help and exit
  -v, --version            Print version and exit
  -c, --command=CMD        Command: start, stop, reload, trace
                           Require args = service name
"""
if __name__ == "__main__":
    from beehive.server import configure_server

    params = configure_server()

    from beehive.module.catalog.consumer import start_catalog_consumer

    start_catalog_consumer(params)
