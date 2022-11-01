#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 11 00:37:16 2022

@author: cihcih
"""

from models import database

from flask import Blueprint, Flask, request, jsonify
import requests
import ast


database_api=Blueprint('database_api', __name__)

'''
@database_api.route("/create", methods=['POST'])
def create_commit_data_api():
    req = request.get_json()
    res = database.get_dbformat_data(req)
    
    return jsonify(res)
'''

# url 裡面不能放冒號
# 用 = 的話，ast.literal_eval 解析不了
@database_api.route("/retrieval", methods=['GET'])
def search_commit_api():
    project_name = request.args.get('projectName')
    keywords = request.args.get('keywords')
    range = request.args.get('range')
    quantity = request.args.get('quantity')

    req = {
        "projectName": project_name,
        "keywords": keywords,
        "range": ast.literal_eval(range),
        "quantity": ast.literal_eval(quantity)
    }

    return jsonify(database.get_word_vector_and_rank(req))

@database_api.route("/getbranches", methods=['GET'])
def get_branches():
    project_name = request.args.get('project')
    print("getproject brances")
    return jsonify(database.get_project_branches(project_name))

@database_api.route("/getredis", methods=['GET'])
def get_redis_data():
    return jsonify(database.get_all_redis_data())

@database_api.route("/clear", methods=['DELETE'])
def delete_all_data_api():
    
    return jsonify(database.delete_all_data())