import streamlit as st
import pandas as pd
import numpy as np
import joblib
import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import warnings
warnings.simplefilter(action='ignore', category=UserWarning)
import urllib.request

# --- フォント設定（Cloudでも文字化けしないように） ---
import matplotlib as mpl
mpl.rcParams.update(mpl.rcParamsDefault)

font_url = "https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP-Regular.otf"
font_path = "/tmp/NotoSansJP-Regular.otf"

try:
    if not os.path.exists(font_path):
        urllib.request.urlretrieve(font_url, font_path)

    jp_font = fm.FontProperties(fname=font_path)
    plt.rcParams['font.family'] = jp_font.get_name()
    plt.rcParams['axes.unicode_minus'] = False

except Exception as e:
    print(f"[フォント読み込みエラー]: {e}")
    jp_font = fm.FontProperties()

# --- 定数とパス ---
MODEL_PATH = "ls_model.pkl"
THRESHOLDS_PATH = "ls_thresholds.pkl"
SPREADSHEET_KEY = "1WARG0Ev0wYJ1Kb1zLwihP0c45gs8Vq-h5Y22biWa7LI"

FEATURE_COLUMNS = [
    "EPS", "PER", "海外", "個人", "証券自己", "信用倍率", "評価損益率",
    "売り残", "買い残", "騰落6日", "騰落10日", "騰落25日",
    "日経レバ倍率", "空売り比率", "VIX", "USDJPY", "SOX"
]

# --- 判定関数（LSと一致） ---
def get_judgment(score, thresholds):
    t1, t2, t3, t4 = thresholds
    if score >= t1:
        return "強気（上昇確率：80%以上）"
    elif score >= t2:
        return "やや強気（上昇確率：60〜70%）"
    elif score >= t3:
        return "中立（拮抗）"
    elif score >= t4:
        return "やや弱気（下落確率：60〜70%）"
    else:
        return "弱気（下落確率：80%以上）"

# --- Streamlit UI ---
st.markdown("""
<div style='text-align:center'>
    <h1>📈 AI日経診断 <span style='font-size:0.7em'>(Takiの投資ラボ)</span></h1>
</div>
""", unsafe_allow_html=True)

st.markdown("""
### 🧠 AIによる日経平均診断
日付を選んで、診断スコア・判定を確認できます。
""")

model = joblib.load(MODEL_PATH)
thresholds = list(map(int, joblib.load(THRESHOLDS_PATH))) if os.path.exists(THRESHOLDS_PATH) else [80, 60, 40, 20]
t1, t2, t3, t4 = thresholds

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials_dict = dict(st.secrets["gcp_service_account"])
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
gc = gspread.authorize(credentials)
ws = gc.open_by_key(SPREADSHEET_KEY).worksheet("LS日経診断")

@st.cache_data(ttl=600)
def load_log_df():
    data = ws.get_all_values()
    headers = data[0]
    rows = data[1:]
    df = pd.DataFrame(rows, columns=headers)
    df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
    df["スコア"] = pd.to_numeric(df["スコア"], errors="coerce")
    df["label"] = pd.to_numeric(df.get("label", np.nan), errors="coerce")
    df["判定"] = df["判定"].fillna("ー")
    return df.dropna(subset=["日付", "スコア"])

log_df = load_log_df()

latest_date = log_df["日付"].max()
st.sidebar.markdown("### 🔍 日付を選択")
selected_date = st.sidebar.date_input("診断日", latest_date)

row = log_df[log_df["日付"] == pd.to_datetime(selected_date)]
if row.empty:
    st.warning("この日付の診断データはありません。")
    st.stop()

score = row["スコア"].values[0]
judgment = get_judgment(score, thresholds)
result = row["判定"].values[0]

st.subheader(f"📅 診断日：{selected_date.strftime('%Y-%m-%d')}")
st.metric("スコア", f"{score:.2f}")
st.markdown("診断",judgment)
st.metric("判定", result)

valid_df = log_df.dropna(subset=["label", "スコア"])
valid_df = valid_df[valid_df["日付"] < pd.to_datetime(selected_date)].copy()

valid_df.loc[:, "prediction"] = valid_df["スコア"].apply(lambda s: "強気" if s >= t2 else "弱気" if s <= t3 else "中立")
valid_df.loc[:, "direction"] = valid_df["label"].apply(lambda l: "上昇" if l == 1 else "下落")
valid_df.loc[:, "hit"] = valid_df.apply(lambda row: (
    (row["prediction"] == "強気" and row["direction"] == "上昇") or
    (row["prediction"] == "弱気" and row["direction"] == "下落")
), axis=1)

pred_total = valid_df["prediction"].isin(["強気", "弱気"]).sum()
hit_count = valid_df["hit"].sum()
hit_rate = hit_count / pred_total if pred_total > 0 else 0

st.metric(
    label="モデル的中率（非中立のみ対象）",
    value=f"{hit_rate:.1%}（{hit_count}/{pred_total}）"
)

st.subheader("📈 スコア推移グラフ") 
from matplotlib.lines import Line2D

fig, ax = plt.subplots(figsize=(8, 3))
plot_df = log_df.sort_values("日付")
ax.plot(plot_df["日付"], plot_df["スコア"], label="スコア", marker='o')

# 的中マーカー追加
plot_df["hit"] = plot_df.apply(lambda row: (
    (row["スコア"] >= t2 and row["label"] == 1) or
    (row["スコア"] <= t3 and row["label"] == 0)
), axis=1)

# prediction列の補完（なければ計算）
if "prediction" not in plot_df.columns:
    plot_df["prediction"] = plot_df["スコア"].apply(lambda s: "強気" if s >= t2 else "弱気" if s <= t3 else "中立")

plot_df["color"] = plot_df.apply(lambda row: (
    "dodgerblue" if row["hit"] else ("orange" if row["prediction"] == "中立" else "gray")
), axis=1)

for color in ["dodgerblue", "orange", "gray"]:
    subset = plot_df[plot_df["color"] == color]
    ax.scatter(subset["日付"], subset["スコア"], color=color, label=color, zorder=5)

for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontproperties(jp_font)

ax.axhline(thresholds[0], color='green', linestyle='--')
ax.axhline(thresholds[1], color='orange', linestyle='--')
ax.axhline(thresholds[2], color='orange', linestyle='--')
ax.axhline(thresholds[3], color='red', linestyle='--')

legend_elements = [
    Line2D([0], [0], color='dodgerblue', marker='o', label='Correct'),
    Line2D([0], [0], color='gray', marker='o', label='Incorrect'),
    Line2D([0], [0], color='orange', marker='o', label='Neutral'),
    Line2D([0], [0], color='green', linestyle='--', label='Bull Line'),
    Line2D([0], [0], color='red', linestyle='--', label='Bear Line'),
    Line2D([0], [0], color='orange', linestyle='--', label='Neutral Line'),
]
legend = ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1.0, 0.5), prop=jp_font)
for text in legend.get_texts():
    text.set_fontproperties(jp_font)

ax.set_xlabel("Date", fontproperties=jp_font)
ax.set_ylabel("Score", fontproperties=jp_font)
ax.grid(True)
st.pyplot(fig)

st.markdown("""
---
【免責事項（Disclaimer）】

本サービスは、過去の市場データおよび統計モデルに基づき、情報提供を目的とするものであり、
将来の株価動向や投資成果を保証するものではありません。

掲載情報は投資判断の参考資料としてご利用ください。
最終的な投資判断はご利用者ご自身の責任で行っていただくものとし、
当方はこれに伴う損失・損害等について一切の責任を負いません。

また、本サービスは金融商品取引法上の投資助言・代理業には該当せず、
特定の金融商品の売買を推奨するものではありません。

一部情報は外部提供データを含んでおり、その正確性・完全性・適時性を保証するものではありません。
情報には遅延、欠落、変更等が生じる可能性があります。

掲載されているアルゴリズム、UI、分析手法、その他一切の知的財産権は開発者に帰属します。
無断での転載・複製・改変・商用利用は固くお断りいたします。
法人でのご利用や商用展開をご希望の場合は、事前にお問い合わせください。

> 本免責事項の内容は、予告なく変更される場合があります。常に最新の内容をご確認ください。
""")