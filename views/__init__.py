#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 11 00:15:26 2022

@author: cihcih
"""


from .crawler_api import crawler_api
from .database_api import database_api
from .bridge_api import bridge_api

blueprint_prefix = [(crawler_api, "/crawler"), (database_api, "/database"), (bridge_api, "/bridge")]

def register_blueprint(app):
    for blueprint, prefix in blueprint_prefix:
        app.register_blueprint(blueprint, url_prefix=prefix)
    return app