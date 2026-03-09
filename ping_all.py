import requests
import datetime
import time

# =====================================================================
# 1. 喚醒目標清單 (加入你所有的 Streamlit App 網址)
# =====================================================================
TARGET_URLS = [
    "https://financedailynews-mobile.streamlit.app/",
    "https://financedailynews-web.streamlit.app/",
    "https://lyu-science-cloud.streamlit.app/",
    "https://ai-biology-lab.streamlit.app/",
    "https://ai-earthscience-lab.streamlit.app/",
    "https://finance-daily-news.streamlit.app/",
    "https://science-truth-portal.streamlit.app/",
    "https://science-ai-lab.streamlit.app/"
]

# =====================================================================
# 2. 網路喚醒邏輯 (對抗冷啟動)
# =====================================================================
def ping_apps():
    print(f"🚀 開始執行喚醒任務 (UTC): {datetime.datetime.now(datetime.timezone.utc)}")
    
    for url in TARGET_URLS:
        success = False
        # 每個網址最多嘗試 3 次，避免因為網路抖動或剛好在重啟而失敗
        for attempt in range(3):
            try:
                # Streamlit 休眠後重新啟動可能需要 15~30 秒，Timeout 必須設長
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    print(f"✅ 成功喚醒: {url}")
                    success = True
                    break
                else:
                    print(f"⚠️ 異常狀態碼 ({response.status_code}): {url}")
            except requests.exceptions.RequestException as e:
                print(f"⏳ 第 {attempt + 1} 次連線失敗 ({url}): 等待 5 秒後重試...")
                time.sleep(5)
                
        if not success:
            print(f"❌ 喚醒失敗，已達最大重試次數: {url}")

# =====================================================================
# 3. 實體檔案修改邏輯 (對抗 GitHub 不活躍判定)
# =====================================================================
def generate_heartbeat_file():
    """
    建立或更新一個文字檔，產生實質的程式碼變動。
    這一步是為了讓後續的 Git Commit 有東西可以推播。
    """
    filename = "system_heartbeat.txt"
    current_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # 覆寫檔案，避免日誌無限膨脹
    with open(filename, "w", encoding="utf-8") as f:
        f.write("=== Streamlit Keep-Alive Heartbeat ===\n")
        f.write(f"Last ping executed at: {current_time}\n")
        f.write("Status: Active\n")
        
    print(f"📝 活躍度檔案 ({filename}) 已更新。")

if __name__ == "__main__":
    ping_apps()
    generate_heartbeat_file()
