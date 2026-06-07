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
    # analyzer.pyから本日分（朝4時〜）の集計データを取得
    study_data = get_weekly_study_time()

# データの存在チェック
if study_data is not None:
    z_scores, _ = calculate_z_scores(study_data)
    slack_prob = predict_slacking_probability(study_data)
    total_exp = sum(study_data.values())
    
    # データが空、または全プロジェクトの合計時間が0の場合のエラー回避用ハンドリング
    if total_exp == 0 or len(study_data) == 0:
        df = pd.DataFrame(columns=["習得スキル（プロジェクト名）", "稼いだ経験値（分）"])
    else:
        df = pd.DataFrame({
            "習得スキル（プロジェクト名）": list(study_data.keys()),
            "稼いだ経験値（分）": list(study_data.values())
        })

    col1, col2, col3 = st.columns([1.2, 1.0, 1.0])

    with col1:
        st.markdown("### 📊 現在のスキル熟練度")
        
        # 朝4時以降、まだ全くタイマーが動いていないとき
        if total_exp == 0:
            st.info("朝4時以降の勉強データはまだ記録されていません。Togglでタイマーをスタートしましょう！")
        else:
            fig = px.bar(
                df, 
                x="習得スキル（プロジェクト名）", 
                y="稼いだ経験値（分）",
                color="習得スキル（プロジェクト名）",
                text="稼いだ経験値（分）",
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            
            fig.update_traces(
                texttemplate='%{text:.1f} EXP', 
                textposition='outside',
                textfont_color='#1e293b'
            )
            
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#1e293b',
            )
            
            fig.update_yaxes(rangemode="tozero", tickfont_color='#1e293b', title_font_color='#1e293b')
            fig.update_xaxes(tickfont_color='#1e293b', title_font_color='#1e293b')
            
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 🧬 育成中のモンスター")
        
        # 1日完結型（朝4時〜）の進化ライン基準
        if total_exp == 0:
            # 経験値ゼロ：モンスターボール
            img_url = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png"
            stage_title = "🧭 ステージ 0: モンスターボール"
            caption_text = "朝4時を過ぎました！まだ今日の経験値が記録されていません。タイマーを回してポケモンを登場させよう！"
        elif total_exp < 60.0:
            # 30分未満：ミニリュウ
            img_url = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-v/black-white/animated/147.gif"
            stage_title = "🐉 ステージ 1: ミニリュウ"
            caption_text = "今日の進化の旅が始まりました。脱皮を繰り返して大きくなります。"
        elif total_exp < 180.0:
            # 1.5時間未満：ハクリュー
            img_url = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-v/black-white/animated/148.gif"
            stage_title = "✨ ステージ 2: ハクリュー"
            caption_text = "オーラをまとって進化！最終進化（カイリュー）まであと一息です。"
        else:
            # 1.5時間以上：カイリュー（最終進化）
            img_url = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-v/black-white/animated/149.gif"
            stage_title = "🧡 ステージ 3: カイリュー（最終進化）"
            caption_text = "本日の最終進化達成！素晴らしいコミット量です。この調子を維持しましょう！"
            
        st.image(img_url, width=120)
        st.caption(f"**{stage_title}**\n\n{caption_text}")

    with col3:
        st.markdown("### 👾 伴走モンスター：ドモ")
        
        if z_scores:
            most_slack_genre = min(z_scores, key=z_scores.get)
        else:
            most_slack_genre = "未設定のクエスト"
        
        # 1日の始まり（EXP=0）はサボり確率を強制的に100%にする
        display_slack_prob = 100.0 if total_exp == 0 else slack_prob
        
        st.write(f"🔮 **本日のサボり予測確率**: `{display_slack_prob}%`")
        
        if display_slack_prob >= 75.0:
            avatar = "   +--------------+\n   |   ( 🔥 益 🔥 ) |\n   +--------------+"
            status_color = "error"
            dialogue = f"【緊急警報】お前さんがこのままサボって1日を終える確率は {display_slack_prob}% だ！タイマーを回して勉強時間を追加し、未来の予測数値を書き換えろ！"
        elif display_slack_prob >= 40.0:
            avatar = "   +--------------+\n   |   ( 📝 _ 📝 ) |\n   +--------------+"
            status_color = "warning"
            dialogue = f"【注意：サボり確率 {display_slack_prob}%】夜間リスクを検知。ダラダラ過ごす前に、サクッと次のクエスト（おすすめ：{most_slack_genre}）を片付けちまおう。"
        else:
            avatar = "   +--------------+\n   |   ( ʘ ‿ ʘ  )b |\n   +--------------+"
            status_color = "success"
            dialogue = f"【状態：快適】アクションを確認したぜ！サボり確率は {display_slack_prob}% に低下。この調子で経験値を積み上げていこう！"

        st.code(avatar, language="text")
        if status_color == "error": st.error(dialogue)
        elif status_color == "warning": st.warning(dialogue)
        else: st.success(dialogue)
            
        st.markdown("#### ⚔️ プレイヤー・ステータス")
        st.metric(label="本日の総獲得EXP", value=f"{total_exp:.1f} 点")
        st.metric(label="次の推奨クエスト", value=most_slack_genre)

else:
    st.info("🔮 ギルド伝言板：Toggl Trackでプロジェクトを作成して、タイマーを回すとここにデータが召喚されます。")
