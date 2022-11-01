#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 18 20:41:21 2022

@author: cihcih
"""

'''
from models import bridge
from time import timezone
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
import redis

def do_job():
    r = redis.Redis(host='localhost', port=6379, decode_responses=True) 
    projects = r.get(key)
    if not(projects == None):
        bridge.append_to_db(projects)

def start_schedule():
    try:
        scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
        scheduler.add_job(do_job, 'cron', day_of_week='1-7', hour=21, minute=6, id="schedule_crawler")
        scheduler.start()
    except:
        return {"status": "scheduler creating failed"}
    return {"status": "scheduler creating completed"}

def end_schedule():
    try:
        scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
        scheduler.remove_job(job_id='schedule_crawler')
        scheduler.start()
    except:
        return {"status": "scheduler removing failed"}
    return {"status": "scheduler removing completed"}
'''