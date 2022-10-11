#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 11 00:38:53 2022

@author: cihcih
"""

from models import crawler

import requests, json
#from flask import Flask, request, jsonify

import redis
# 英文斷詞＆詞性還原
import nltk
nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')
nltk.download('omw-1.4')
nltk.download('punkt')
from nltk import word_tokenize, pos_tag
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer

# 中文斷詞
import monpa
# 停用詞
from nltk.corpus import stopwords
nltk.download('stopwords')

import time

import numpy as np
#為了算cosine
from numpy import dot
from numpy.linalg import norm
import re

# -------------- [Create] 建立詞向量，並儲存至 DB - START -------------- #

# 拿到單字詞性
def get_word_pos(tag):
    # 會需要還原的是形容詞、動詞、名詞、副詞
    if tag.startswith('J'):
        return wordnet.ADJ
    elif tag.startswith('V'):
        return wordnet.VERB
    elif tag.startswith('N'):
        return wordnet.NOUN
    elif tag.startswith('R'):
        return wordnet.ADV
    else:
        return None
    
# 包含中英斷詞＆詞性還原＆去除停用詞
def pre_process(sentence):
    
    #英文斷詞
    sentence = sentence.lower() #轉小寫
    token_en = word_tokenize(sentence) #英文斷詞
    tagged = pos_tag(token_en) #拿到詞性
    
    #詞性還原
    wnl = WordNetLemmatizer()
    lemmas = []
    for tag in tagged:
        wordnet_pos = get_word_pos(tag[1]) or wordnet.NOUN #不需要還原的就通通給名詞
        lemmas.append(wnl.lemmatize(tag[0], pos=wordnet_pos))
    
    #中文斷詞
    token_ch = []
    for word in lemmas:
        token_ch += monpa.cut(word)
        
    #去除停用詞
    stop_words = stopwords.words('english')
    stop_words += ['.', ',', '[', ']', '{', '}', ':'] # 加上我認為的 英文
    stop_words += ['，','。', '「', '」', '！', '？'] # 加上我認為的 中文
    word = [word for word in token_ch if word not in stop_words]
    
    return word

# 印出 commit 紀錄，參數為 create API 的 request
def print_commit_history(request):
    for commit in request["commitHistory"]:
        print(f'{commit["sha"]} - {commit["document"]}')
     
# 算 tf分數，同時順便算 corpus 相關數據（termnum, term）
def get_tf_score(document):
    tf_score = {}
    termnum_in_document = 0
    termnum_in_corpus = 0
    term_in_corpus = {}
    
    # 資料前處理
    term_in_document = pre_process(document)
    
    #計算tf-iwf
    for word in term_in_document:
        #iwf - 計算 corpus 中有多少 term
        termnum_in_corpus += 1
        #tf - 計算每個 term 出現幾次
        termnum_in_document += 1
        if word not in tf_score:
            tf_score[word] = 1
        else:
            tf_score[word] += 1
    
    term_in_corpus = tf_score #這時的 tf_score 還是記次數的
    tf_score = {key: tf_score[key]/termnum_in_document for key in term_in_document}

    
    return {"message": document,
            "tf_score": tf_score,
            "termnum_in_corpus": termnum_in_corpus, 
            "term_in_corpus": term_in_corpus}

# 合併 dictionary，如果 key 相同，則 value 相加
def merge_dict(d1, d2):
    all_keys = d1.keys() | d2.keys()
    merge_dict = {key: (d1.get(key) if d1.get(key) is not None else 0) 
              + (d2.get(key) if d2.get(key) is not None else 0) 
              for key in all_keys}
    
    return merge_dict
    
# 算 tf分數，並把所需的東西都轉成要存進 db 的格式
def get_dbformat_data(request):
    time_start = time.time() #開始計時
    r = redis.Redis(host='localhost', port=6379, decode_responses=True) 
    
    #project_data = get_project(r)
    #project_data['num'] += 1
    
    try:
        for pro in request:
            pro_info = {"allRepo" : [],
                        "corpusTerm" : {},
                        "corpusTermNum" : 0}
            for repo in request[pro]:
                pro_info["allRepo"].append(repo)
                #要存到 DB 的 data
                data = {"documents" : [],
                        "project" : pro }
                
                #計算 tf 分數
                for commit in request[pro][repo]:
                    result = get_tf_score(commit["message"])
                    
                    temp = {"id": commit["id"],
                            "message": result["message"],
                            "tfScore": result["tf_score"] } #一開始記出現次數，後來記 tf分數
                    data["documents"].append(temp)
                    
                    pro_info["corpusTermNum"] += result["termnum_in_corpus"]
                    pro_info["corpusTerm"] = merge_dict(pro_info["corpusTerm"], result["term_in_corpus"])
                res = create_to_db(repo, data, r)
                if res!="ok":
                    return res
        
            create_to_db(pro, pro_info, r)
        time_end = time.time() #結束計時
        print(f"花費時間: {time_end - time_start}秒")
        return {"status": "indexing completed"}
    except:
        return {"status": "indexing failed"}

# 把計算完的資料存到 database 裡
def create_to_db(key, value, r):
    try:
        json_data = json.dumps(value)
        r.set(key, json_data)
        #json.loads(r.get(key))
    except:
        return f"key [{key}] create failed"
    return "ok"

def get_project(r):
    project_data = r.get('projectData')
    
    if project_data != None:
        return json.loads(project_data)
    return {"projects":[],
            "num" : 0}

# -------------- [Create] 建立詞向量，並儲存至 DB - END -------------- #


# -------------- [Read] 輸入關鍵字，回傳排行 - START -------------- #

# 計算 cosine 相似度並排名，參數為 commit_data 是因為需要 sha
def get_cosine_rank(search_vector, commit_data):
    cosine_rank = []
    
    for commit in commit_data:
        temp = {}
        temp["id"] = commit["id"]
        temp["message"] = commit["message"]
        temp["repo"] = commit["repo"]
        temp["cosine"] = dot(search_vector, commit["wordVector"])/(norm(search_vector)*norm(commit["wordVector"]))
        cosine_rank.append(temp)
    cosine_rank = sorted(cosine_rank, key=lambda d: d['cosine'], reverse=True)
    return cosine_rank

# cosine rank -> rank（把不重要的刪掉）
def consine_rank_to_rank(cosine_rank, num):
    response = []
    
    for commit in cosine_rank:
        temp = {}
        temp["repo"] = commit["repo"]
        temp["id"] = commit["id"]
        temp["message"] = commit["message"]
        #temp["cosine"] = commit["cosine"]
        if commit["cosine"] != 0:
            response.append(temp)
        
    if len(response)==0:
        return "all cosine is 0"
    response = response[:int(num) if (num!="" and int(num)<len(response)) else len(response)]
    
    
    return response

# 處理 range 後面是:*的
def get_all_range_branch(pro_name, branch_range, r):
    for b in branch_range:
        if b.split(":")[-1] == "*":
            branch_range.remove(b)
            info = re.split(',|:', b)
            
            data = r.get(pro_name)
            if data == None:
                return None
            source = json.loads(data)
            if source["allRepo"] == None:
                return None
            
            for r in source["allRepo"]:
                if re.split(',|:', r)[0] == info[0] and re.split(',|:', r)[1]==info[1]:
                    branch_range.append(r)
    return branch_range


# 重新計算 corpus 相關資料，並計算 word vector
def get_word_vector_and_rank(request):
    time_start = time.time() #開始計時
    
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    request["range"] = get_all_range_branch(request["projectName"], request["range"], r)
    pro_info = get_project_info(request["projectName"], request["range"], r)
    if pro_info == None:
        return {"status": "search failed", "rank": {}}
    
    print("first")
    #先算跟 corpus 相關的
    search_data = get_tf_score(request["keywords"])
    corpus_term_temp = merge_dict(pro_info["corpusTerm"], search_data["term_in_corpus"])
    corpus_termnum_temp = pro_info["corpusTermNum"] + search_data["termnum_in_corpus"]
    # search_data["tf_score"] tf的分數
    
    #計算詞向量(tf-iwf)
    #print("----------- 詞向量 ----------")
    # 計算詞向量(key為sha值，value為詞向量)
    history = []
    for repo in request["range"]:
        repo_mes = json.loads(r.get(repo))["documents"]
        
        for commit in repo_mes:
            commit["repo"] = repo
            commit["wordVector"] = []
            for term in corpus_term_temp:
                #如果有這個字就加上他的 tf-iwf
                if term in commit["tfScore"]:
                    commit["wordVector"].append(commit["tfScore"][term]*np.log10(corpus_termnum_temp/corpus_term_temp[term]))
                else:
                    commit["wordVector"].append(0)
            history.append(commit)
    
    search_data["wordVector"] = []
    for term in corpus_term_temp:
        if term in search_data["tf_score"]:
            search_data["wordVector"].append(search_data["tf_score"][term]*np.log10(corpus_termnum_temp/corpus_term_temp[term]))
        else:
            search_data["wordVector"].append(0)
    
    #比較 cosine 相似度
    cosine_rank = get_cosine_rank(search_data["wordVector"], history)
    
    time_end = time.time() #結束計時
    print(f"花費時間: {time_end - time_start}秒")
    return {"status": "search completed", "rank": consine_rank_to_rank(cosine_rank, request["quantity"])}

def get_project_info(pro_name, repo_list, r):
    data = r.get(pro_name)
    if data == None:
        return None
    source = json.loads(data)
    if source["allRepo"] == None:
        return None
    
    match = 0
    
    print(source["allRepo"])
    for repo in repo_list:
        print(f"repo: {repo}")
        if repo in source["allRepo"]:
            match+=1
        else:
            break
    print(f"match: {match}, length: {len(repo_list)}")
    if match == len(repo_list):
        return {"corpusTerm" : source["corpusTerm"],
                "corpusTermNum" : source["corpusTermNum"]}
    return None

# -------------- [Read] 輸入關鍵字，回傳排行 - END -------------- #




# -------------- [Read] 讀取 DB - START -------------- #

def get_all_redis_data():
    data = []
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        for element in r.keys():
            data.append({element: json.loads(r.get(element))})
        return data
    except:
        return "can't get redis data"
    
# -------------- [Read] 讀取 DB - END -------------- #
    
# -------------- [Delete] 刪除 repository - START -------------- #

def delete_project(request):
    
    try:
        delete = False
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        pros = r.get("projectData")
        if pros == None:
            return "project data is empty!"
        value = json.loads(pros)
        
        for pro in value["projects"]:
            if pro["projectId"] in request["range"]:
                for repo in pro["all_repo"]:
                    r.delete(repo)
                value["projects"] = value["projects"].remove(pro)
                delete = True
                
        
        if delete==False:
            return "some project id don't exit"
        json_data = json.dumps(value)
        r.set("projectData", json_data)
        
        return "deleting completed"
    except:
        return "deleting failed"


def delete_all_data():
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        for element in r.keys():
            r.delete(element)
        return {"status": "deleting completed"}
    except:
        return {"status": "deleting failed"}

# -------------- [Delete] 刪除 repository - END -------------- #
    
    