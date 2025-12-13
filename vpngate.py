import requests
import csv
import io
import socket
import os
from datetime import datetime

# تنظیمات
VPNGATE_API_URL = "http://www.vpngate.net/api/iphone/"
TIMEOUT = 1.5  # ثانیه برای تست اتصال
OUTPUT_DIR = "proxies"
PAC_FILE = "proxy.pac"

def get_servers():
    try:
        response = requests.get(VPNGATE_API_URL)
        text = response.text.replace("#HostName", "HostName") # اصلاح هدر برای CSV
        # رد کردن خطوط اضافی اول فایل
        lines = text.split('\n')
        csv_data = []
        start_reading = False
        for line in lines:
            if line.startswith("HostName"):
                start_reading = True
            if start_reading and line.strip() != "*" and line.strip() != "":
                csv_data.append(line)
        
        return csv.reader(csv_data)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def is_alive(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        result = sock.connect_ex((ip, int(port)))
        sock.close()
        return result == 0
    except:
        return False

def generate_pac(proxies):
    js_content = "function FindProxyForURL(url, host) {\n"
    for proxy in proxies:
        # فرض بر اینه که پروکسی‌ها ساکس یا اچ‌تی‌تی‌پی هستن، اینجا نمونه SOCKS5
        js_content += f"    // {proxy['country']}\n"
    
    # ساختار ساده PAC (بیشتر برای نمونه، چون VPNGate اکثرا OpenVPN/L2TP هستن نه پروکسی مرورگر)
    # اما اگر آی‌پی‌ها رو برای پروکسی میخوای، این خط رو کانفیگ کن:
    proxy_list = "; ".join([f"PROXY {p['ip']}:{p['port']}" for p in proxies[:50]])
    js_content += f"    return '{proxy_list}; DIRECT';\n}}"
    return js_content

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    csv_reader = get_servers()
    headers = next(csv_reader, None)
    
    if not headers:
        print("No data found.")
        return

    # پیدا کردن ایندکس ستون‌ها
    try:
        ip_idx = headers.index("IP")
        port_idx = headers.index("Port") # معمولا پورت OpenVPN یا L2TP
        country_idx = headers.index("CountryShort")
        proto_idx = headers.index("OpenVPN_ConfigData_Base64") # فقط برای اینکه بدونیم دیتا هست
    except ValueError:
        print("CSV headers mismatch.")
        return

    valid_proxies = []
    
    print("Fetching and testing servers (Limit: Top 100 recent)...")
    
    count = 0
    for row in csv_reader:
        if len(row) < len(headers) or count > 100: # محدودیت برای جلوگیری از تایم‌اوت گیت‌هاب
            continue
            
        ip = row[ip_idx]
        port = row[port_idx] # توجه: این معمولا پورت TCP نیست، پورت VPN هست.
        country = row[country_idx]
        
        # تست اتصال ساده
        if is_alive(ip, 443) or is_alive(ip, 80) or is_alive(ip, port):
            print(f"✅ {country} - {ip}")
            valid_proxies.append({'ip': ip, 'port': port, 'country': country})
            
            # ذخیره بر اساس کشور
            with open(f"{OUTPUT_DIR}/{country}.txt", "a") as f:
                f.write(f"{ip}:{port}\n")
        
        count += 1

    # ساخت فایل PAC
    with open(PAC_FILE, "w") as f:
        f.write(generate_pac(valid_proxies))
    
    print(f"Done. Found {len(valid_proxies)} alive servers.")

if __name__ == "__main__":
    main()
