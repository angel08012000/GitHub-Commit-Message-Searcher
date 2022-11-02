#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 18 20:41:21 2022

@author: cihcih
"""


from models import crawler, database
from time import timezone
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import redis
import ast

def do_job():
    r = redis.Redis(host='localhost', port=6379, decode_responses=True) 
    req = {"allProjects":ast.literal_eval(r.get("allProjects"))}
    if req== None:
        print("沒有資料要更新")
    else:
        temp = crawler.get_commit_history(req)
        res = database.get_dbformat_data(temp)

        suc = 0
        if res["status"] == "getting completed":
            res = database.append_to_db(req)
            
            if res["status"] == "indexing completed":
                suc=1
            
        if suc==1:
            print("更新資料成功")
        else:
            print("更新資料失敗")
        
    
    # projects = r.get(key)
    # if not(projects == None):
    #     bridge.append_to_db(projects)

def start_schedule():
    try:
        scheduler = BackgroundScheduler(timezone='Asia/Taipei')
        scheduler.add_job(do_job, 'cron', day_of_week='0-6', hour=8, minute=0, id="schedule_crawler")
        scheduler.start()
    except:
        return {"status": "scheduler creating failed"}
    return {"status": "scheduler creating completed"}