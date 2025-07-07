# 📈 AI日経診断アプリ

AIによる日経平均株価のスコア診断・可視化を行うStreamlitアプリです。  

---

## 🔍 主な機能

- ✅ 日付ごとのスコア・診断結果の表示
- 📊 スコアの推移グラフ
- 🎯 モデル的中率の自動計算（非中立予測のみ対象）

---

## 🚀 デプロイ方法（Streamlit Cloud）

1. [Streamlit Cloud](https://streamlit.io/cloud) にログイン
2. GitHub連携し、このリポジトリを選択
3. `app.py` をメインファイルとして指定
4. `requirements.txt` により必要ライブラリが自動インストールされます
5. `Secrets` に以下の内容を追加：

## 📁 ファイル構成

```
├── app.py              # Streamlit アプリ本体
├── requirements.txt    # 必要ライブラリ
└── .streamlit/
    └── secrets.toml    # 認証情報（GitHubにはアップしない）
```

---

## ⚠️ 免責事項

本アプリは投資助言ではなく、将来の株価や投資成果を保証するものではありません。  
投資判断はご自身の責任でお願いいたします。

---

## 🧑‍💻 開発者

[Taki-Toushi-Lab](https://github.com/Taki-Toushi-Lab)

---

## 📜 ライセンス

このプロジェクトはMITライセンスのもとで公開されています。
