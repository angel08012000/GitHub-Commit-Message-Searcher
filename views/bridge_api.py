#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 11 00:43:51 2022

@author: cihcih
"""

from models import bridge

from flask import Blueprint, Flask, request, jsonify
from time import timezone
from apscheduler.schedulers.background import BackgroundScheduler


bridge_api=Blueprint('bridge_api', __name__)

@bridge_api.route("/register", methods=['POST'])
def get_commit_and_create_api():
    try:
        req = request.get_json()
        scheduler = BackgroundScheduler(timezone='Asia/Taipei')
        scheduler.add_job(bridge.register, args=[req])
        scheduler.start()
        return jsonify({"status": "recieve completed"})
        
    except:
        return jsonify({"status": "recieve failed"})