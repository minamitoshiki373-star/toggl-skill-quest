import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta, timezone
import zoneinfo  # 👈 日本時間の判定用にインポート
from dotenv import load_dotenv
import numpy as np

def get_weekly_study_time():
    """
    関数名はそのままですが、内部処理を「今日の朝4時〜現在」のTogglログのみを
    抽出・集計する仕様に変更しています。
    """
    load_dotenv()
    api_key = os.getenv("TOGGL_API_KEY")
    password = "api_token"

    if not api_key:
        print("[エラー] TOGGL_API_KEY が設定されていません。")
        return None

    # ⏰ 日本時間の「朝4時リセット」に合わせた開始時刻を計算
    tokyo_tz = zoneinfo.ZoneInfo("Asia/Tokyo")
    now_tokyo = datetime.now(tokyo_tz)

    if now_tokyo.hour < 4:
        start_date_tokyo = (now_tokyo - timedelta(days=1)).replace(hour=4, minute=0, second=0, microsecond=0)
    else:
        start_date_tokyo = now_tokyo.replace(hour=4, minute=0, second=0, microsecond=0)

    # Toggl APIが受け付けるISO 8601形式（+09:00付き）に変換
    start_str = start_date_tokyo.isoformat()
    end_str = now_tokyo.isoformat()

    # ① まず、Workspace内の「プロジェクト一覧」を取得してIDと名前のマッピングを作る
    proj_url = "https://api.track.toggl.com/api/v9/me/projects"
    try:
        proj_res = requests.get(proj_url, auth=HTTPBasicAuth(api_key, password), timeout=10)
        project_map = {}
        if proj_res.status_code == 200:
            for p in proj_res.json():
                project_map[p["id"]] = p["name"]
    except Exception as e:
        print(f"[警告] プロジェクト一覧の取得に失敗: {e}")
        project_map = {}

    # ② 今日の朝4時以降のタイムエントリー（履歴）を取得
    url = "https://api.track.toggl.com/api/v9/me/time_entries"
    params = {"start_date": start_str, "end_date": end_str}

    try:
        response = requests.get(url, auth=HTTPBasicAuth(api_key, password), params=params, timeout=10)
        if response.status_code != 200:
            return None

        entries = response.json()
        
        # 動的に見つかったプロジェクトだけで集計枠を初期化
        study_summary = {name: 0.0 for name in project_map.values()}
        study_summary["No Project"] = 0.0

        for entry in entries:
            duration_sec = entry.get("duration", 0)
            if duration_sec < 0:  # 現在計測中のものは除外
                continue
                
            duration_min = duration_sec / 60.0
            project_id = entry.get("project_id")
            
            # プロジェクト名を取得、なければ "No Project"
            project_name = project_map.get(project_id, "No Project")
            
            if project_name not in study_summary:
                study_summary[project_name] = 0.0
            study_summary[project_name] += duration_min

        # 一度も使われていない "No Project" は見栄えのために削除
        if study_summary["No Project"] == 0:
            del study_summary["No Project"]

        return study_summary

    except requests.exceptions.RequestException as e:
        print(f"[通信エラー] {e}")
        return None

def calculate_z_scores(study_summary):
    """
    偏りの評価を廃止。単純に各プロジェクトの学習時間をそのまま返し、
    一番時間が少ないプロジェクトを「次にやるべきクエスト」として特定するためだけの関数。
    """
    if not study_summary or len(study_summary) == 0:
        return {}, 0
    
    z_scores = {key: round(val, 2) for key, val in study_summary.items()}
    return z_scores, 0

def predict_slacking_probability(study_summary):
    """
    今日サボる確率を計算するロジック。
    1日の合計学習時間（EXP）が増えるほど、サボり確率がリアルタイムに減少します。
    """
    # 💡 安全対策：データが取れない、または空の場合はサボり確率100%を確実に返す
    if not study_summary or len(study_summary) == 0:
        return 100.0
    
    total_time = sum(study_summary.values())
    if total_time == 0:
        return 100.0

    tokyo_tz = zoneinfo.ZoneInfo("Asia/Tokyo")
    now_tokyo = datetime.now(tokyo_tz)
    current_hour = now_tokyo.hour
    
    # ベースのサボり確率（夜になるほど高くなる）
    base_probability = 30.0
    if current_hour >= 22:
        base_probability += 50.0
    elif current_hour >= 20:
        base_probability += 35.0
    elif current_hour >= 18:
        base_probability += 15.0
    
    # 勉強時間が追加されたら、時間帯リスクをマイナス補正
    base_probability -= (total_time * 2.0)  # 1分ごとに2%減少

    final_probability = max(0.0, min(100.0, base_probability))
    
    # 今まさに机に向かって合計時間が少しでも動いているなら、強制的に数値を下げる
    if final_probability > 40.0:
        final_probability = 25.0
        
    # 💡 最後に必ず round() で囲った数値を返すように徹底（Noneが返るのを防ぐ）
    return round(float(final_probability), 1)
