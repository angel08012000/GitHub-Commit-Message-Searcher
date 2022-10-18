#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 11 00:43:51 2022

@author: cihcih
"""

from models import crawler, database

from flask import Blueprint, Flask, request, jsonify
import requests


bridge_api=Blueprint('bridge_api', __name__)

@bridge_api.route("/register", methods=['POST'])
def get_commit_and_create_api():
    req = request.get_json()
    temp = crawler.get_commit_history(req)
    res = database.get_dbformat_data(temp)
    
    return jsonify(res)