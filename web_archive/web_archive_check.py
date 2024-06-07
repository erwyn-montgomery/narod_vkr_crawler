import requests
import time


def check_archive(url):
    try:
        url = f"{url}.narod.ru"
        api_url = f"http://archive.org/wayback/available?url={url}"
        response = requests.get(api_url, timeout=10)
        status = False
        timestamp = None
        if response.status_code == 200:
            data = response.json()
            status = data.get("archived_snapshots", {}).get("closest", {}).get("available", False)
            timestamp_raw = data.get("archived_snapshots", {}).get("closest", {}).get("timestamp", None)
            if timestamp_raw:
                try:
                    timestamp = f"{timestamp_raw[:4]}-{timestamp_raw[4:6]}-{timestamp_raw[6:8]} {timestamp_raw[8:10]}:{timestamp_raw[10:12]}:{timestamp_raw[12:]}"
                except:
                    pass
            if status:
                return f"archived=True timestamp={timestamp}"
            else:
                return "archived=False"
        else:
            return "archived=False"
    except:
        return "archived=False"
    

def main(file):
    with open(file) as f:
        narod = [line.rstrip() for line in f]
    for site in narod:
        status = check_archive(site)
        with open("web_archive_results_600k.txt", "a") as f:
            f.write(f"{site} {status}\n")
        time.sleep(1)


if __name__ == "__main__":
    main("narod_domains.txt")
