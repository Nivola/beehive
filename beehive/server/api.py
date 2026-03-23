# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

import gevent.monkey
gevent.monkey.patch_all()

import os
from beehive.common.flask_app import BeehiveApp


################################################################################
# app section
################################################################################
# Create app

# entrypoint uwsgi

if os.environ.get("DEBUG_APISPEC") == "YES":
    # moneky patch functions such that on error (or warnings)
    # more details are available in pod logs

    import logging
    logging.getLogger("flasgger").setLevel(logging.DEBUG)
    logging.getLogger("apispec").setLevel(logging.DEBUG)
    logging.getLogger("marshmallow").setLevel(logging.DEBUG)
    import apispec.ext.marshmallow.openapi as am_openapi

    _orig_schema2jsonschema = am_openapi.OpenAPIConverter.schema2jsonschema

    def debug_schema2jsonschema(self, schema, **kwargs):
        print(">>> Converting schema:", schema)
        return _orig_schema2jsonschema(self, schema, **kwargs)

    am_openapi.OpenAPIConverter.schema2jsonschema = debug_schema2jsonschema

    import flasgger.base
    import traceback
    import marshmallow

    # Save original function
    _real_get_apispecs = flasgger.base.Swagger.get_apispecs

    def debug_get_apispecs(self, *args, **kwargs):
        print("\n=== get_apispecs CALLED ===")

        try:
            specs = _real_get_apispecs(self, *args, **kwargs)
            print(">>> get_apispecs RETURNED successfully, scanning ...")
        except Exception as e:
            print("\n!!! ERROR inside get_apispecs BEFORE returning !!!")
            traceback.print_exc()
            raise

        # Walk returned dictionary for marshmallow.missing
        def walk(o, path="root"):
            if o is marshmallow.missing:
                print(">>> FOUND _Missing at:", path)
            elif isinstance(o, dict):
                for k, v in o.items():
                    walk(v, f"{path}.{k}")
            elif isinstance(o, (list, tuple)):
                for i, v in enumerate(o):
                    walk(v, f"{path}[{i}]")

        walk(specs)
        return specs

    # Patch it
    flasgger.base.Swagger.get_apispecs = debug_get_apispecs

app = BeehiveApp(__name__)

if os.environ.get("DEBUG_UWSGI") == "YES":
    import beecell.debug
