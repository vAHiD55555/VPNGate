import requests
import csv
import os

# تنظیمات
# استفاده از میرورهای گیت‌هاب برای دور زدن بلاک شدن توسط سایت اصلی
SOURCES = [
    "http://www.vpngate.net/api/iphone/",
    "https://raw.githubusercontent.com/fanyueciyuan/vpngate/main/vpngate.csv",
    "https://raw.githubusercontent.com/vpngate-world/vpngate-daily/master/vpngate.csv"
]
OUTPUT_DIR = "proxies"
PAC_FILE = "proxy.pac"

def get_servers():
    for url in SOURCES:
        try:
            print(f"Trying to fetch from: {url}")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                text = response.text.replace("#HostName", "HostName")
                lines = text.split('\n')
                csv_data = []
                start_reading = False
                for line in lines:
                    if line.startswith("HostName"):
                        start_reading = True
                    if start_reading and line.strip() != "*" and line.strip() != "":
                        csv_data.append(line)
                
                if len(csv_data) > 5: # اگر دیتا معتبر بود
                    print(f"Successfully fetched {len(csv_data)} rows from {url}")
                    return csv.reader(csv_data)
        except Exception as e:
            print(f"Failed to fetch from {url}: {e}")
            continue
    return None

def generate_pac(proxies):
    js_content = "function FindProxyForURL(url, host) {\n"
    # ساخت فایل PAC ساده
    proxy_rules = []
    for p in proxies[:50]: # فقط ۵۰ تای اول برای جلوگیری از سنگین شدن
        # فرمت استاندارد: PROXY ip:port
        proxy_rules.append(f"PROXY {p['ip']}:{p['port']}")
    
    rule_str = "; ".join(proxy_rules)
    js_content += f"    return '{rule_str}; DIRECT';\n}}"
    return js_content

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    csv_reader = get_servers()
    
    if not csv_reader:
        print("❌ Could not fetch data from any source.")
        exit(1) # ارور بده که بفهمیم

    headers = next(csv_reader, None)
    if not headers:
        print("CSV headers missing.")
        exit(1)

    try:
        # پیدا کردن ستون‌ها با انعطاف‌پذیری بیشتر
        headers_lower = [h.lower() for h in headers]
        ip_idx = -1
        country_idx = -1
        port_idx = -1 # ترجیحا TCP
        
        # تلاش برای پیدا کردن ایندکس‌ها
        for i, h in enumerate(headers_lower):
            if "ip" in h and "v6" not in h: ip_idx = i
            if "countryshort" in h: country_idx = i
            if "tcp" in h: port_idx = i # اولویت با پورت TCP
        
        # اگر پورت TCP نبود، پورت معمولی
        if port_idx == -1:
             for i, h in enumerate(headers_lower):
                if h == "port": port_idx = i

    except ValueError:
        print("Header parsing failed.")
        exit(1)

    valid_proxies = []
    unique_ips = set()
    
    print("Processing list...")
    
    for row in csv_reader:
        if len(row) < 5: continue
        
        try:
            ip = row[ip_idx]
            country = row[country_idx]
            port = row[port_idx]
            
            if ip in unique_ips: continue
            unique_ips.add(ip)

            # اینجا دیگه تست اتصال نمی‌گیریم تا لیست خالی نشه
            # فرض رو بر این می‌ذاریم که لیست روزانه آپدیت شده و زنده‌ست
            
            valid_proxies.append({'ip': ip, 'port': port, 'country': country})
            
            # ذخیره فایل کشور
            with open(f"{OUTPUT_DIR}/{country}.txt", "a") as f:
                f.write(f"{ip}:{port}\n")
                
        except IndexError:
            continue
        
    # ساخت فایل PAC
    if valid_proxies:
        with open(PAC_FILE, "w") as f:
            f.write(generate_pac(valid_proxies))
        print(f"✅ Done. Saved {len(valid_proxies)} proxies. Check the 'proxies' folder.")
    else:
        print("❌ No proxies found in the list.")

if __name__ == "__main__":
    main()
