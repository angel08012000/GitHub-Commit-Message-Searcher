#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 18 20:52:36 2022

@author: cihcih
"""

from models import schedule

from flask import Blueprint, Flask, request, jsonify


schedule_api=Blueprint('schedule_api', __name__)

@schedule_api.route("/start", methods=['GET'])
def start():
    res = schedule.start_schedule()
    
    return jsonify(res)