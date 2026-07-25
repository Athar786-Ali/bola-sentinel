import urllib.request
import json
import time

base_url = "http://localhost:3000"
test_users_file = "datasets/juice_shop/test_users.json"

def make_request(url, data=None, headers=None):
    if headers is None:
        headers = {}
    if data is not None:
        data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return response.getcode(), json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode()) if e.read() else {}
    except Exception as e:
        print(f"Error: {e}")
        return 500, {}

def register_and_login(email, password):
    reg_data = {
        "email": email,
        "password": password,
        "passwordRepeat": password,
        "securityQuestion": {"id": 1},
        "securityAnswer": "answer"
    }
    make_request(f"{base_url}/api/Users", data=reg_data)
    
    login_data = {"email": email, "password": password}
    status, resp = make_request(f"{base_url}/rest/user/login", data=login_data)
    
    if status == 200:
        data = resp["authentication"]
        return data["token"], data["umail"], data["bid"], data.get("id", data["bid"]) # user_id might be id or bid
    else:
        print(f"Failed to login {email}: {status}")
        return None, None, None, None

def create_address(token):
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "country": "Test",
        "fullName": "Test User",
        "mobileNum": 1234567890,
        "zipCode": "12345",
        "streetAddress": "Test Street",
        "city": "Test City",
        "state": "Test State"
    }
    status, resp = make_request(f"{base_url}/api/Addresss", data=data, headers=headers)
    if status == 201:
        return resp["data"]["id"]
    print(f"Failed to create address: {status} {resp}")
    return None

def main():
    token_a, email_a, bid_a, uid_a = register_and_login("user_a@test.com", "password123")
    token_b, email_b, bid_b, uid_b = register_and_login("user_b@test.com", "password123")
    
    addr_a = create_address(token_a)
    addr_b = create_address(token_b)
    
    # We use actual user ID (or basket ID if user ID is missing) as the primary user_id
    # The BOLA targets are addresses and baskets.
    test_users = {
        "user_a": {
            "auth_header": f"Bearer {token_a}",
            "user_id": str(uid_a),
            "owned_object_ids": {
                "baskets": [str(bid_a)],
                "addresses": [str(addr_a)]
            }
        },
        "user_b": {
            "auth_header": f"Bearer {token_b}",
            "user_id": str(uid_b),
            "owned_object_ids": {
                "baskets": [str(bid_b)],
                "addresses": [str(addr_b)]
            }
        }
    }
    
    with open(test_users_file, "w") as f:
        json.dump(test_users, f, indent=2)
        
    print(f"Created {test_users_file}")

if __name__ == "__main__":
    main()
