import os
import json
import base64
import docker

from flask import Flask, request, jsonify


def get_var(name):
    var = os.getenv(name)
    if not var:
        raise ValueError(f"You didn't provide env var `{name}`")
    return var

docker_client = docker.from_env()

CONFIG_FILE = get_var("CONFIG_FILE")
SUB_FILE = get_var("SUB_FILE")
TOKEN = get_var("TOKEN")
PORT = get_var("PORT")
TITLE = os.getenv("TITLE") or "Xray Pult"

XRAY_NAME = 'xray-server'

app = Flask(__name__)

@app.route('/add_user', methods=['POST'])
def add_user():
    """
    Add a new user to Xray
    Expected JSON payload: {"id": "username", "token": "token"}
    """
    try:
        data = request.get_json()
        
        if data["token"] != TOKEN:
            return jsonify({"error": "Invalid token"}), 401

        if not data or 'id' not in data:
            return jsonify({"error": "Missing 'id' field in request body"}), 400
        
        user_id = data['id'].strip()
        
        if not user_id:
            return jsonify({"error": "User ID cannot be empty"}), 400
        
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        for client in config['inbounds'][0]['settings']['clients']:
            if client["id"] == user_id:
                return jsonify({"error": "User ID already exists"}), 400

        config['inbounds'][0]['settings']['clients'].append({
            "id": user_id,
            "flow": ""
        })
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        xray_container = docker_client.containers.get(XRAY_NAME)
        xray_container.restart()

        return jsonify({
            "message": f"User '{user_id}' added successfully",
            "total_users": len(config['inbounds'][0]['settings']['clients']),
            "all_users": [client["id"] for client in config['inbounds'][0]['settings']['clients']],
        }), 201
        
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON in request body"}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/del_user', methods=['POST'])
def del_user():
    """
    Delete user from Xray
    Expected JSON payload: {"id": "username", "token": "token"}
    """
    try:
        data = request.get_json()
       
        if data["token"] != TOKEN:
            return jsonify({"error": "Invalid token"}), 401

        if not data or 'id' not in data:
            return jsonify({"error": "Missing 'id' field in request body"}), 400
        
        user_id = data['id'].strip()
        
        if not user_id:
            return jsonify({"error": "User ID cannot be empty"}), 400
        
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        for client in config['inbounds'][0]['settings']['clients']:
            if client["id"] == user_id:
                config['inbounds'][0]['settings']['clients'].remove(client)
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        xray_container = docker_client.containers.get(XRAY_NAME) 
        xray_container.restart()

        return jsonify({
            "message": f"User '{user_id}' removed successfully",
            "total_users": len(config['inbounds'][0]['settings']['clients']),
            "all_users": [client["id"] for client in config['inbounds'][0]['settings']['clients']],
        }), 201
        
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON in request body"}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/sub/<idx>', methods=['GET'])
def sub(idx):
    """Generates subscription for user"""
    # TODO: implement checking and some kimd of security
    try:
        with open(SUB_FILE, "r") as s:
            ctx = s.read()
    
        ctx = ctx.replace("$CLIENT$", idx)
        sub_bytes = ctx.encode("utf-8")
        sub = base64.b64encode(sub_bytes).decode()

        title = base64.b64encode(
                TITLE.encode("utf-8")
        ).decode()

        response = app.make_response(sub)
                
        response.headers['profile-title'] = f'base64:{title}'

        return response
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

app.run(host='0.0.0.0', port=PORT, debug=False)
