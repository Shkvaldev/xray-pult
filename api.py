import os
import json
import docker
import base64
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
        
        # Check if user exists in any inbound
        user_exists = False
        for inbound in config.get('inbounds', []):
            if 'settings' in inbound and 'clients' in inbound['settings']:
                for client in inbound['settings']['clients']:
                    if client.get("id") == user_id:
                        user_exists = True
                        break
                if user_exists:
                    break
        
        if user_exists:
            return jsonify({"error": "User ID already exists"}), 400

        # Add user to all inbounds that have a clients setting
        for inbound in config.get('inbounds', []):
            if 'settings' in inbound and 'clients' in inbound['settings']:
                inbound['settings']['clients'].append({
                    "id": user_id,
                    "flow": ""
                })

        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        xray_container = docker_client.containers.get(XRAY_NAME)
        xray_container.restart()

        # Calculate total users across all inbounds
        total_users = 0
        all_users = []
        for inbound in config.get('inbounds', []):
            if 'settings' in inbound and 'clients' in inbound['settings']:
                clients = inbound['settings']['clients']
                total_users += len(clients)
                all_users.extend([client["id"] for client in clients])
        
        # Remove duplicates if needed (if same user added to multiple inbounds with different flows)
        all_users = list(set(all_users))

        return jsonify({
            "message": f"User '{user_id}' added successfully to all inbounds",
            "total_users": total_users,
            "all_users": all_users,
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
        
        # Remove user from all inbounds
        removed_count = 0  # Track how many times user was removed
        for inbound in config.get('inbounds', []):
            if 'settings' in inbound and 'clients' in inbound['settings']:
                clients = inbound['settings']['clients']
                # Use list comprehension to filter out the user
                initial_len = len(clients)
                inbound['settings']['clients'] = [
                    client for client in clients if client.get("id") != user_id
                ]
                removed_count += initial_len - len(inbound['settings']['clients'])
        
        if removed_count == 0:
            return jsonify({"error": "User ID not found"}), 404

        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        xray_container = docker_client.containers.get(XRAY_NAME) 
        xray_container.restart()

        # Calculate remaining users
        total_users = 0
        all_users = []
        for inbound in config.get('inbounds', []):
            if 'settings' in inbound and 'clients' in inbound['settings']:
                clients = inbound['settings']['clients']
                total_users += len(clients)
                all_users.extend([client["id"] for client in clients])
        
        all_users = list(set(all_users))  # Remove duplicates

        return jsonify({
            "message": f"User '{user_id}' removed successfully from {removed_count} inbounds",
            "total_users": total_users,
            "all_users": all_users,
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
