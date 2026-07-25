import json

routes = json.load(open('/tmp/js_static_test.json'))
gt = []

# Known vulnerable patterns in Juice Shop
vulnerable_endpoints = {
    'PUT_/api/BasketItems/:id_426',
    'PUT_/api/Addresss/:id_450',
    'PATCH_/rest/products/reviews_634',
    'POST_/rest/basket/:id/checkout_604',
    'PUT_/rest/basket/:id/coupon/:coupon_605',
    'PUT_/rest/order-history/:id/delivery-status_625'
}

for r in routes:
    # Explicitly mark known safe routes that have ownership checks or denyAll
    safe_endpoints = {
        'DELETE_/api/Addresss/:id_451',
        'DELETE_/api/Cards/:id_441',
        'PUT_/api/Cards/:id_440',
        'DELETE_/api/Products/:id_371',
        'PUT_/api/Recycles/:id_389',
        'DELETE_/api/Recycles/:id_390'
    }
    
    is_vulnerable = r['route_id'] in vulnerable_endpoints
    
    # Many POST routes without :id parameters are naturally not BOLA (like /login)
    if 'id' not in r['endpoint'].lower() and r['route_id'] not in vulnerable_endpoints:
        is_vulnerable = False

    entry = {
        "route_id": r['route_id'],
        "http_method": r['http_method'],
        "endpoint": r['endpoint'],
        "actually_vulnerable": is_vulnerable
    }
    gt.append(entry)

with open('datasets/ground_truth/juice-shop.json', 'w') as f:
    json.dump(gt, f, indent=2)

print(f"Generated datasets/ground_truth/juice-shop.json with {len(gt)} entries.")
print(f"Vulnerable routes: {sum(1 for x in gt if x['actually_vulnerable'])}")
