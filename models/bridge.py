#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 18 19:29:18 2022

@author: cihcih
"""
import requests
from models import crawler, database

def register(req):
    temp = crawler.get_commit_history(req)
    res = database.get_dbformat_data(temp)
    mes = "failed"
    if res["status"] == "getting completed":
        res = database.append_to_db(req)
        if res["status"] == "indexing completed":
            mes = "completed"
    
    r = requests.get(f"http://192.168.100.44:10050/commitment/status?message={mes}")

    # r.status_code 伺服器回應的狀態碼
    # requests.codes.ok 成功的狀態碼，也就是 200
    if r.status_code==requests.codes.ok and r.text=="ok":
        print("通知成功！")
    else:
        print("通知失敗！")