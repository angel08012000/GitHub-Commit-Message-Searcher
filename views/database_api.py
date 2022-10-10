#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 11 00:37:16 2022

@author: cihcih
"""

from models import database

from flask import Blueprint, Flask, request, jsonify
import requests


database_api=Blueprint('database_api', __name__)

@database_api.route("/create", methods=['POST'])
def create_commit_data_api():
    req = request.get_json()
    res = database.get_dbformat_data(req)
    
    return jsonify(res)

@database_api.route("/search", methods=['POST'])
def search_commit_api():
    req = request.get_json()

    return jsonify(database.get_word_vector_and_rank(req))

@database_api.route("/getredis", methods=['GET'])
def get_redis_data():
    
    return jsonify(database.get_all_redis_data())

@database_api.route("/delete/all", methods=['DELETE'])
def delete_all_data_api():
    
    return jsonify(database.delete_all_data())