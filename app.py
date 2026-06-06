import streamlit as st
import plotly.express as px
import pandas as pd
from analyzer import get_weekly_study_time, calculate_z_scores, predict_slacking_probability

st.set_page_config(page_title="Skill Quest", page_icon="🎮", layout="wide")

st.markdown("""
    <style>
    /* アプリ全体の背景色と文字色を強制固定 */
    .stApp { 
        background-color: #ffffff !important; 
        color: #1e293b !important; 
    }
    /* プレイヤー・ステータス（st.metric）の文字色を強制的に濃いグレーにする */
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
        color: #1e293b !important;
    }
    .stMetric { 
        background-color: #f8fafc; 
        padding: 15px; 
        border-radius: 10px; 
        border: 2px solid #3b82f6; 
    }
    code { 
        color: #0f172a !important; 
        background-color: #f1f5f9 !important; 
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎮 Skill Quest")
st.subheader("〜 経験値（Togglログ）を稼いで、モンスターを育てよう！ 〜")
st.markdown("---")

with st.spinner("📜 ギルドの通信魔術（Toggl API）で進捗を同期中..."):
    study_data = get_weekly_study_time()

if study_data and len(study_data) > 0:
    z_scores, _ = calculate_z_scores(study_data)
    slack_prob = predict_slacking_probability(study_data)
    total_exp = sum(study_data.values())
    
    df = pd.DataFrame({
        "習得スキル（プロジェクト名）": list(study_data.keys()),
        "稼いだ経験値（分）": list(study_data.values())
    })

    col1, col2, col3 = st.columns([1.2, 1.0, 1.0])

    with col1:
        st.markdown("### 📊 現在のスキル熟練度")
        fig = px.bar(
            df, 
            x="習得スキル（プロジェクト名）",
            y="稼いだ経験値（分）",
            color="習得スキル（プロジェクト名）",
            text="稼いだ経験値（分）",
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#1e293b'),
            yaxis=dict(
                rangemode="tozero",
                tickfont=dict(color='#1e293b'),
                titlefont=dict(color='#1e293b')
            ),
            xaxis=dict(
                tickfont=dict(color='#1e293b'), #
                titlefont=dict(color='#1e293b')
            )
        )

        fig.update_traces(
            texttemplate='%{text:.1f} EXP', 
            textposition='outside',
            textfont=dict(color='#1e293b') #
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 🧬 育成中のモンスター")
        
        # 【修正】確実に表示される公式画像パス（GIFアニメーション）へ変更
        # ポケモン進化ライン：ミニリュウ(147) ➔ ハクリュー(148) ➔ カイリュー(149)
        if total_exp == 0:
            # 経験値ゼロ：タマゴ（404エラー対策としてGitHubの安定したアセットを使用）
            img_url = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png" # 確実に存在するモンスターボール画像
            stage_title = "🧭 ステージ 0: 未孵化のボール"
            caption_text = "まだ経験値が記録されていません。タイマーを回して孵化させましょう！"
        elif total_exp < 60.0:
            # 1時間未満：ミニリュウ
            img_url = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-v/black-white/animated/147.gif"
            stage_title = "🐉 ステージ 1: ミニリュウ"
            caption_text = "進化の旅が始まりました。脱皮を繰り返して大きくなります。"
        elif total_exp < 180.0:
            # 3時間未満：ハクリュー
            img_url = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-v/black-white/animated/148.gif"
            stage_title = "✨ ステージ 2: ハクリュー"
            caption_text = "オーラをまとって進化！フルレンダリング（カイリュー）まであと一息です。"
        else:
            # 3時間以上：カイリュー
            img_url = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-v/black-white/animated/149.gif"
            stage_title = "🧡 ステージ 3: カイリュー（完成体）"
            caption_text = "最終進化達成！素晴らしいコミット量です。この調子を維持しましょう！"
            
        # 画像を表示
        st.image(img_url, width=120)
        st.caption(f"**{stage_title}**\n\n{caption_text}")

    with col3:
        st.markdown("### 👾 伴走モンスター：ドモ")
        # 次に進めるべきおすすめ（一番時間が少ないもの）を特定するロジックのみ残す
        most_slack_genre = min(z_scores, key=z_scores.get)
        
        st.write(f"🔮 **本日のサボり予測確率**: `{slack_prob}%`")
        
        if slack_prob >= 75.0:
            avatar = "   +--------------+\n   |   ( 🔥 益 🔥 ) |\n   +--------------+"
            status_color = "error"
            dialogue = f"【緊急警報】お前さんがこのままサボって1日を終える確率は {slack_prob}% だ！タイマーを回して勉強時間を追加し、未来の予測数値を書き換えろ！"
        elif slack_prob >= 40.0:
            avatar = "   +--------------+\n   |   ( 📝 _ 📝 ) |\n   +--------------+"
            status_color = "warning"
            dialogue = f"【注意：サボり確率 {slack_prob}%】夜間リスクを検知。ダラダラ過ごす前に、サクッと次のクエスト（おすすめ：{most_slack_genre}）を片付けちまおう。"
        else:
            avatar = "   +--------------+\n   |   ( ʘ ‿ ʘ  )b |\n   +--------------+"
            status_color = "success"
            dialogue = f"【状態：快適】アクションを確認したぜ！サボり確率は {slack_prob}% に低下。この調子で経験値を積み上げていこう！"

        st.code(avatar, language="text")
        if status_color == "error": st.error(dialogue)
        elif status_color == "warning": st.warning(dialogue)
        else: st.success(dialogue)
            
        st.markdown("#### ⚔️ プレイヤー・ステータス")
        st.metric(label="今週の総獲得EXP", value=f"{total_exp:.1f} 点")
        st.metric(label="次の推奨クエスト", value=most_slack_genre)

else:
    st.info("🔮 ギルド伝言板：Toggl Trackでプロジェクトを作成して、タイマーを回すとここにデータが召喚されます。")
