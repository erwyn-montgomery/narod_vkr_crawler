import requests
import time


def check_archive(url):
    try:
        url = url.replace("http://", "")
        if url.endswith("/"):
            url = url[:-1]
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
                    timestamp = f"{timestamp_raw[:4]}-{timestamp_raw[4:6]}-{timestamp_raw[6:8]}_{timestamp_raw[8:10]}:{timestamp_raw[10:12]}:{timestamp_raw[12:]}"
                except:
                    pass
            if status:
                return f"archived=True timestamp={timestamp}"
            else:
                return "archived=False timestamp=None"
        else:
            return "archived=False timestamp=None"
    except:
        return "archived=False timestamp=None"
    

def main(file):
    with open(file) as f:
        narod_line = [line.rstrip() for line in f]
    for narod in narod_line:
        try:
            narod_id, site = narod.split()
            status = check_archive(site)
            with open("web_archive_results_sample.txt", "a") as f:
                f.write(f"{narod_id} {site} {status}\n")
            time.sleep(1)
        except Exception as e:
            with open("web_archive_results_sample_error.txt", "a") as f:
                f.write(f"{narod}: {e}\n")


if __name__ == "__main__":
    main("sample_pages_with_id.txt")
