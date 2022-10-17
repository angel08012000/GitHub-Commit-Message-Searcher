#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 10 23:55:54 2022

@author: cihcih
"""

from flask import Blueprint, Flask, request, jsonify
import requests
import json
from bs4 import BeautifulSoup
import time

# -------------- [GET] 拿到 commit 資訊 - START -------------- #

def get_branches(userName, repoName):
    get_branch_url = f'https://api.github.com/repos/{userName}/{repoName}/branches'
    
    # 使用 GET 方式呼叫 GitHub API，拿到所有 branch
    r = requests.get(get_branch_url)
    if r.status_code!=requests.codes.ok:
        return f"failed"
    response = json.loads(r.text) # str to json
    
    branches = []
    for b in response:
        if b["name"] not in branches:
            branches.append(b["name"])
            
    if "main" in branches:
        branches.remove("main")
        branches.insert(0, "main")
    
    print(f"branch 總數: {len(branches)}")
    return branches

# 拿到 commit 紀錄，變成 create API request 的格式（自己測試用）
def get_commit_history(request):
    time_start = time.time() #開始計時
    
    for pro in request["allProjects"]: #一個專案
        pro_name = pro["projectName"]
        print("+--------------------+")
        print(f"專案名稱: {pro_name}")
        data = []
        commit_data = {"projectName": pro_name,
                       "branches" : []} #處理回傳值
        for repo in pro["repoNames"]: #一個repo
            branches = get_branches(repo["userName"], repo["repoName"])
            if branches == "failed":
                return {"status": "crawler failed", "data": {}}
            total = 0
            flag = True
            shas = []
            
            for branch in branches: #一個branch
                print(f"現在分支: {branch}")
                next_page = f'https://github.com/{repo["userName"]}/{repo["repoName"]}/commits/{branch}'
                temp = []
                flag = True
                print("+----------+")
                while flag:
                    response = requests.get(next_page)
                    soup = BeautifulSoup(response.text, "html.parser")
                    commit = soup.find_all("div", class_="flex-auto min-width-0 js-details-container Details")
                    for c in commit:
                        summary = c.find_all("a", class_="Link--primary text-bold js-navigation-open markdown-title")[-1]
                        sha = summary.get("href").split('/')[-1]
                        if sha in shas:
                            continue
                        shas.append(sha)
                        detail = c.find_all("pre", class_="text-small ws-pre-wrap")
                        commit_text = summary.getText() + ("" if detail==[] else detail[0].getText())
                        temp.append({"id": sha, "message": commit_text})
                        print(sha)
                        print(commit_text)
                        print("+----------+")
                        total += 1
                    tag = soup.find_all('a', {'class':'btn btn-outline BtnGroup-item','rel': 'nofollow'})
                    if tag==[]: #如果commit只有1頁
                        flag = False
                        continue
                    tag = tag[-1]
                    next_page = tag.get('href')
                    print(f"下一頁: {next_page}")
                    
                    if next_page == None or tag.getText()!="Older":
                        flag = False
                
                if temp != []:
                    commit_data["branches"].append({"branchName": f'{repo["userName"]},{repo["repoName"]}:{branch}',
                                                    "commit": temp})
                    #commit_data[pro_name][f'{repo["userName"]},{repo["repoName"]}:{branch}'] = temp #處理回傳值
            data.append(commit_data)
            print(f"總共有{total}筆 commit")
    time_end = time.time()    #結束計時

    print(f"花費時間: {time_end - time_start}秒")
    return {"status": "crawler completed", "data": data}
    
# -------------- [GET] 拿到 commit 資訊 - END -------------- #
