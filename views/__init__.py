#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 11 00:15:26 2022

@author: cihcih
"""


from .database_api import database_api
from .bridge_api import bridge_api
from .schedule_api import schedule_api

blueprint_prefix = [(database_api, ""), (bridge_api, ""), (schedule_api, "/schedule")]
# blueprint_prefix = [(database_api, ""), (bridge_api, "")]

def register_blueprint(app):
    for blueprint, prefix in blueprint_prefix:
        app.register_blueprint(blueprint, url_prefix=prefix)
    return app