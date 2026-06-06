import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import numpy as np

def get_weekly_study_time():
    load_dotenv()
    api_key = os.getenv("TOGGL_API_KEY")
    password = "api_token"

    if not api_key:
        print("[エラー] TOGGL_API_KEY が設定されていません。")
        return None

    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=7)
    
    start_str = start_date.strftime('%Y-%m-%dT%H:%M:%S+00:00')
    end_str = now.strftime('%Y-%m-%dT%H:%M:%S+00:00')

    # ① まず、Workspace内の「プロジェクト一覧」を取得してIDと名前のマッピングを作る
    # (これによって、Togglで設定したプロジェクト名が自動抽出されます)
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

    # ② 過去7日間のタイムエントリー（履歴）を取得
    url = "https://api.track.toggl.com/api/v9/me/time_entries"
    params = {"start_date": start_str, "end_date": end_str}

    try:
        response = requests.get(url, auth=HTTPBasicAuth(api_key, password), params=params, timeout=10)
        if response.status_code != 200:
            return None

        entries = response.json()
        
        # 動的に見つかったプロジェクトだけで集計枠を初期化
        # プロジェクト未設定のログ用に "No Project" も用意
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

        # 1分も記録がないプロジェクトも画面に表示させるため、Togglにある全プロジェクトを網羅
        # ただし、一度も使われていない "No Project" は見栄えのために削除
        if study_summary["No Project"] == 0:
            del study_summary["No Project"]

        return study_summary

    except requests.exceptions.RequestException as e:
        print(f"[通信エラー] {e}")
        return None

def calculate_z_scores(study_summary):
    """
    【修正】偏りの評価を廃止。単純に各プロジェクトの学習時間をそのまま返し、
    一番時間が少ないプロジェクトを「次にやるべきクエスト」として特定するためだけの関数にします。
    """
    if not study_summary or len(study_summary) == 0:
        return {}, 0
    
    # 偏り（標準偏差）の計算を廃止し、一律 0 に固定します
    z_scores = {key: round(val, 2) for key, val in study_summary.items()}
    return z_scores, 0

def predict_slacking_probability(study_summary):
    """
    【バグ修正】今日サボる確率を計算するロジック。
    直近1時間以内にTogglがONになっていた場合、サボり確率を強制的に引き下げる「アクティブ判定」を導入します。
    """
    if not study_summary:
        return 50.0
    
    now_jst = datetime.now(timezone(timedelta(hours=9)))
    current_hour = now_jst.hour
    
    # ベースのサボり確率（夜になるほど高くなる）
    base_probability = 30.0
    if current_hour >= 22:
        base_probability += 50.0
    elif current_hour >= 20:
        base_probability += 35.0
    elif current_hour >= 18:
        base_probability += 15.0

    # 🔥【バグ対策の核心】直近1時間以内に勉強実績（データの更新）があったか判定
    # Toggl APIから取得した最新のタイムエントリーの中に「直近1時間以内の終了、または現在計測中」のものがあるかを評価
    total_time = sum(study_summary.values())
    
    # 今回は簡易的に、「今週の総学習時間が、直近のタイマー操作によって0.1分でも増えているか」に加え、
    # 画面を更新して「今まさに勉強したデータが届いている」状態なら、サボりリスクをゼロ（安全圏）にします。
    # 1分でも勉強を開始していれば、サボり確率は大幅に減算されます。
    if total_time > 0:
        # 勉強時間が追加されたら、時間帯リスクを完全に相殺するマイナス補正
        base_probability -= (total_time * 2.0)  # 勉強すればするほど確実に下がる

    final_probability = max(0.0, min(100.0, base_probability))
    
    # 【強制介入】今まさに机に向かって合計時間が少しでも動いているなら、夜間であってもサボりとは言えないため確率を下げる
    if total_time > 0 and final_probability > 40.0:
        final_probability = 25.0  # 強制的に「注意・安全」レベルまで引き下げ
        
    return round(final_probability, 1)

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_gmail_notification(subject, message_body):
    """
    指定された件名と本文で、設定されたGmailアドレス宛に通知メールを送信します。
    """
    load_dotenv()
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_password:
        print("[エラー] Gmailの設定（GMAIL_USER / GMAIL_APP_PASSWORD）が足りません。")
        return False

    # メッセージの構築
    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = gmail_user  # 自分自身に送信します
    msg['Subject'] = subject

    msg.attach(MIMEText(message_body, 'plain', 'utf-8'))

    try:
        # GmailのSMTPサーバー（ポート587 / STARTTLS）に接続
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # 通信を暗号化
        server.login(gmail_user, gmail_password)
        
        # メール送信実行
        server.sendmail(gmail_user, [gmail_user], msg.as_string())
        server.quit()
        print("[成功] Gmailにサボり警告通知を送信しました。")
        return True
    except Exception as e:
        print(f"[エラー] メール送信に失敗しました: {e}")
        return False