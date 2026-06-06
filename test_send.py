# test_send.py
from analyzer import get_weekly_study_time, calculate_z_scores, predict_slacking_probability, send_gmail_notification

print("🔄 Togglデータを取得中...")
study_data = get_weekly_study_time()

if study_data is not None:
    z_scores, _ = calculate_z_scores(study_data)
    slack_prob = predict_slacking_probability(study_data)
    
    # 3時間未満を想定したデフォルトのおすすめ（仮）
    most_slack_genre = min(z_scores, key=z_scores.get) if z_scores else "なし"
    
    # ドモのセリフを構築（app.pyのロジックを流用）
    if slack_prob >= 75.0:
        dialogue = f"【緊急警報】南さんがこのままサボって1日を終える確率は {slack_prob}% だ！タイマーを回して勉強時間を追加し、未来の予測数値を書き換えろ！"
    elif slack_prob >= 40.0:
        dialogue = f"【注意：サボり確率 {slack_prob}%】夜間リスクを検知。ダラダラ過ごす前に、サクッと次のクエスト（おすすめ：{most_slack_genre}）を片付けちまおう。"
    else:
        dialogue = f"【状態：快適】アクションを確認したぜ！サボり確率は {slack_prob}% に低下。この調子で経験値を積み上げていこう！"

    # メールの本文を作成
    subject = f"🎮 Skill Quest：ドモからの定期報告 (サボり確率 {slack_prob}%)"
    body = f"ドモだ。現在のステータスを報告するぜ。\n\n{dialogue}\n\n現在の熟練度データ:\n{study_data}"
    
    print("📧 メールを送信します...")
    send_gmail_notification(subject, body)
else:
    print("Togglデータの取得に失敗したため、テストを中断しました。")