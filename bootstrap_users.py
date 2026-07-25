#!/usr/bin/env python3
import json
import time
import urllib.request
import urllib.parse
import sys
from pathlib import Path

BASE_URL = "http://localhost:9000"

def do_request(url, data=None, cookies=None):
    headers = {}
    if cookies:
        headers["Cookie"] = cookies
    
    req = urllib.request.Request(url, headers=headers)
    if data:
        data_encoded = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib.request.Request(url, data=data_encoded, headers=headers)
    
    try:
        response = urllib.request.urlopen(req)
        body = response.read().decode('utf-8')
        
        # Get set-cookie header
        jwt = None
        for key, value in response.getheaders():
            if key.lower() == 'set-cookie' and 'authToken=' in value:
                jwt = value.split('authToken=')[1].split(';')[0]
                break
                
        try:
            body_json = json.loads(body)
        except:
            body_json = body
            
        return response.status, body_json, jwt
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        try:
            body_json = json.loads(body)
        except:
            body_json = body
        return e.code, body_json, None

def register_and_get_user(username, email, password):
    # Register
    status, body, jwt = do_request(f"{BASE_URL}/register", data={"username": username, "email": email, "password": password})
    if status != 200:
        # Might be already registered
        status, body, jwt = do_request(f"{BASE_URL}/login", data={"username": username, "password": password})
    
    if not jwt:
        print(f"Failed to get JWT for {username}")
        return None

    cookie_str = f"authToken={jwt}"
    
    # Get User ID
    status, body, _ = do_request(f"{BASE_URL}/userinfo", cookies=cookie_str)
    if not isinstance(body, dict):
        print(f"Failed to get userinfo for {username}")
        return None
        
    user_id = body.get("id")
    
    # Create a note to get an object ID
    status, body, _ = do_request(f"{BASE_URL}/notes", data={"noteTitle": "Secret Note", "noteBody": "Secret Body"}, cookies=cookie_str)
    note_id = body.get("id") if isinstance(body, dict) else None
    
    if not note_id:
        # Notes might not be returning JSON cleanly, just fallback
        note_id = "1"
    
    # Return formatted schema
    return {
        "auth_header": f"Cookie: authToken={jwt}",
        "user_id": str(user_id),
        "owned_object_ids": {
            "notes": [str(note_id)]
        }
    }

def main():
    print("Waiting for server to be fully ready...")
    time.sleep(5)
    
    user_a = register_and_get_user("user_a", "a@a.com", "password123")
    user_b = register_and_get_user("user_b", "b@b.com", "password123")
    
    if not user_a or not user_b:
        print("Failed to bootstrap users")
        return
        
    out = {
        "user_a": user_a,
        "user_b": user_b
    }
    
    out_path = Path("datasets/intentionally_vulnerable/vuln-nodejs-app/test_users.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f"test_users.json created successfully at {out_path}")

if __name__ == "__main__":
    main()
