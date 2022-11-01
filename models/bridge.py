#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 18 19:29:18 2022

@author: cihcih
"""
import redis
from models import crawler, database

def register(req):
    temp = crawler.get_commit_history(req)
    res = database.get_dbformat_data(temp)
    if res["status"] == "indexing completed":
        res = database.append_to_db(req)
    return res