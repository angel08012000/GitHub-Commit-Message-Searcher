#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 11 00:24:44 2022

@author: cihcih
"""

from models import crawler

from flask import Blueprint, Flask, request, jsonify
import requests


crawler_api=Blueprint('crawler_api', __name__)

@crawler_api.route('/commit', methods=['POST'])
def get_commit_api():
    req = request.get_json()
    res = crawler.get_commit_history(req)
    
    return jsonify(res)