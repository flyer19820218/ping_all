import requests
import time

# 把您所有需要喚醒的網址貼在這裡
APPS = [
    "https://lyu-science-cloud.streamlit.app/",
    "https://ai-biology-lab.streamlit.app/",
    "https://ai-earthscience-lab.streamlit.app/",
    "https://finance-daily-news.streamlit.app/",
    "https://science-truth-portal.streamlit.app/",
    "https://science-ai-lab.streamlit.app/"
]

def wake_up():
    print(f"--- 開始喚醒任務：{time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    for url in APPS:
        try:
            # 模擬瀏覽器訪問
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                print(f"✅ 成功喚醒: {url}")
            else:
                print(f"⚠️ 狀態異常 ({response.status_code}): {url}")
        except Exception as e:
            print(f"❌ 喚醒失敗: {url}, 錯誤: {e}")

if __name__ == "__main__":
    wake_up()
