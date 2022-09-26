#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 12 16:16:35 2022

@author: cihcih
"""

# 引入模組
import requests
import sys
import json

import numpy as np
#為了算cosine
from numpy import dot
from numpy.linalg import norm

# --------------------------------------- #

# 英文斷詞＆詞性還原
import nltk
#nltk.download('averaged_perceptron_tagger')
#nltk.download('wordnet')
#nltk.download('omw-1.4')
from nltk import word_tokenize, pos_tag
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer

# 中文斷詞
import monpa

# 停用詞
from nltk.corpus import stopwords
#nltk.download('stopwords')

# 資料庫
import redis

# flask
from flask import Flask, request, jsonify

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

# 拿到 commit 紀錄，變成 create API request 的格式（自己測試用）
def get_commit_history(user_name, repository_name):
    
    get_commit_url = f"https://api.github.com/repos/{user_name}/{repository_name}/commits"
    #get_commit_url = f"https://api.github.com/repos/sheng-kai-wang/TABot/commits"
    
    # 使用 GET 方式呼叫 GitHub API
    r = requests.get(get_commit_url)
    if r.status_code!=requests.codes.ok:
        sys.exit(f"{r.status_code}獲取 API 失敗！")
        
    response = json.loads(r.text) # str to json

    # 把我需要的東西存下來
    request = {"userName": user_name, "repositoryName": repository_name, "commitHistory": []}
    for commit in response:
        temp = {}
        temp["sha"] = commit["sha"]
        temp["document"] = commit["commit"]["message"]
        request["commitHistory"].append(temp)
    
    return request

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
    r = redis.Redis(host='localhost', port=6379, decode_responses=True) 
    
    project_data = get_project(r)
    project_data['num'] += 1
    pro_info = {"projectId" : project_data['num'],
                "all_repo" : [],
                "corpusTerm" : {},
                "corpusTermNum" : 0}
    
    for repo in request["all_document"]:
        pro_info["all_repo"].append(repo)
        #要存到 DB 的 data
        data = {"documents" : [],
                "project" : project_data['num'] }
        
        #計算 tf 分數
        for commit in request["all_document"][repo]:
            result = get_tf_score(commit)
            
            temp = {"message": result["message"],
                    "tfScore": result["tf_score"] } #一開始記出現次數，後來記 tf分數
            data["documents"].append(temp)
            
            pro_info["corpusTermNum"] += result["termnum_in_corpus"]
            pro_info["corpusTerm"] = merge_dict(pro_info["corpusTerm"], result["term_in_corpus"])
        res = create_to_db(repo, data, r)
        if res!="ok":
            return "indexing failed"
        
    project_data["projects"].append(pro_info)
    create_to_db("projectData", project_data, r)
    return "indexing completed"

# 把計算完的資料存到 database 裡
def create_to_db(key, value, r):
    try:
        json_data = json.dumps(value)
        r.set(key, json_data)
        #json.loads(r.get(key))
    except:
        return "failed"
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
        temp["message"] = commit["message"]
        temp["cosine"] = dot(search_vector, commit["wordVector"])/(norm(search_vector)*norm(commit["wordVector"]))
        cosine_rank.append(temp)
    cosine_rank = sorted(cosine_rank, key=lambda d: d['cosine'], reverse=True)
    return cosine_rank

# cosine rank -> rank（把不重要的刪掉）
def consine_rank_to_rank(cosine_rank, num):
    response = {"rank": []}
    
    for commit in cosine_rank:
        response["rank"].append(commit["message"])
        
    response["rank"] = response["rank"][:int(num) if (num!="" and int(num)<len(response["rank"])) else len(response["rank"])]
        
    return response

# 重新計算 corpus 相關資料，並計算 word vector
def get_word_vector_and_rank(request):
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    pro_info = get_project_info(request["range"], r)
    if pro_info == None:
        return "repo range error (not in same project)"
    
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
    
    return consine_rank_to_rank(cosine_rank, request["quantity"])

def get_project_info(repo_list, r):
    source = json.loads(r.get("projectData"))
    source = source["projects"]
    
    for pro in source:
        match = 0
        for repo in repo_list:
            if repo in pro["all_repo"]:
                match+=1
            else:
                break
        if match == len(repo_list):
            return {"corpusTerm" : pro["corpusTerm"],
                    "corpusTermNum" : pro["corpusTermNum"]}
    return None

# -------------- [Read] 輸入關鍵字，回傳排行 - END -------------- #

def get_all_redis_data():
    data = []
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        for element in r.keys():
            data.append({element: json.loads(r.get(element))})
        return data
    except:
        return "can't get redis data"

# -------------- [Delete] 刪除 repository - START -------------- #

def delete_repository(request):
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        for repo in request["range"]:
            r.delete(repo)
        return "deleting completed"
    except:
        return "deleting failed"


def delete_all_data():
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        for element in r.keys():
            r.delete(element)
        return "deleting completed"
    except:
        return "deleting failed"

# -------------- [Delete] 刪除 repository - END -------------- #

app = Flask(__name__)

@app.route("/get_commit", methods=['POST'])
def get_commit_data_api():
    req = request.get_json()
    
    commit_history = get_commit_history(req["userName"], req["repositoryName"])
    print_commit_history(commit_history)
    
    return jsonify(commit_history)

@app.route("/create", methods=['POST'])
def create_commit_data_api():
    req = request.get_json()
    res = get_dbformat_data(req)
    
    return jsonify(res)

@app.route("/search", methods=['POST'])
def search_commit_api():
    req = request.get_json()

    return jsonify(get_word_vector_and_rank(req))

@app.route("/getredis", methods=['GET'])
def get_redis_data():
    
    return jsonify(get_all_redis_data())

@app.route("/delete", methods=['DELETE'])
def delete_repository_api():
    req = request.get_json()
    
    return jsonify(delete_repository(req))

@app.route("/delete/all", methods=['DELETE'])
def delete_all_data_api():
    
    return jsonify(delete_all_data())
    

# 如果把 app.py 當成主程式的話
# 就啟動伺服器 //app.run()
if __name__ == "__main__":
	# debug=True 代表你即使改了程式碼，也不用 ctrl+C 關掉重開
	app.run(host='0.0.0.0', port=8082, debug=True)

