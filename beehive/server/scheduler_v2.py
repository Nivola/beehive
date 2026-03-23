#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

"""
Usage: scheduler.py config_file

Options:
  -h, --help               Print help and exit
  -v, --version            Print version and exit
  -c, --command=CMD        Command: start, stop, reload, trace
                           Require args = service name
"""

"""
import ssl

# If ssl.wrap_socket has been removed (Python 3.12+), recreate it safely
if not hasattr(ssl, "wrap_socket"):
    def wrap_socket(sock, keyfile=None, certfile=None, server_side=False,
                    cert_reqs=ssl.CERT_NONE, ssl_version=ssl.PROTOCOL_TLS_CLIENT,
                    ca_certs=None, do_handshake_on_connect=True,
                    suppress_ragged_eofs=True, ciphers=None):
        ctx = ssl.SSLContext(ssl_version)

        ctx.verify_mode = cert_reqs

        if ca_certs:
            ctx.load_verify_locations(ca_certs)
        if certfile:
            ctx.load_cert_chain(certfile, keyfile)

        if ciphers:
            ctx.set_ciphers(ciphers)

        return ctx.wrap_socket(
            sock,
            server_side=server_side,
            do_handshake_on_connect=do_handshake_on_connect,
            suppress_ragged_eofs=suppress_ragged_eofs,
        )

    ssl.wrap_socket = wrap_socket
"""
if __name__ == "__main__":
    # entry point for beat pods
    from beehive.server import configure_server

    params = configure_server()

    from beehive.common.task_v2.manager import start_scheduler

    start_scheduler(params)
