# MLB日本人選手 LINE速報

毎朝7時にMLBの日本人選手の前日成績をLINEに送るシステム。

## 送られてくるメッセージ例

```
⚾ MLB日本人選手成績
2025/5/12 (現地時間)
────────────────────

【大谷翔平】 LAD
  NYM 3-5 LAD
  投：7.0回 4安 1失 2四球 10奪三振  ◎勝
  今季：防御率2.18  5勝2敗  72奪三振
  打：2/4  1本 3打点
  今季：打率.315  12本  38打点  OPS1.025

【今永昇太】 CHC
  CHC 4-2 STL
  投：6.0回 5安 2失 1四球 7奪三振
  今季：防御率3.15  5勝2敗  61奪三振
```

---

## セットアップ手順

### 1. LINE Messaging API の設定（10〜15分）

#### 1-1. LINE Developersでチャネルを作成
1. [LINE Developers](https://developers.line.biz/) にアクセス（LINEアカウントでログイン）
2. 「プロバイダー」を作成（例：「私のMLBBot」）
3. 「Messaging API」チャネルを新規作成
   - チャネル名：「MLB速報」など好きな名前
   - その他は適当でOK

#### 1-2. チャネルアクセストークンを取得
1. 作成したチャネルを開く
2. 「Messaging API設定」タブ →「チャネルアクセストークン（長期）」→「発行」
3. 表示されたトークンをコピー・保存（後でGitHub Secretsに登録）

#### 1-3. 自分のLINEユーザーIDを取得
1. 「Messaging API設定」タブ → QRコードをスマホで読み取ってBotを友だち追加
2. [webhook.site](https://webhook.site/) にアクセスし、表示されるURLをコピー
3. LINE DevelopersでWebhook URLに貼り付け → 「検証」
4. スマホのLINEでBotに適当なメッセージを送る
5. webhook.siteの画面で受信したJSONの中の `"userId": "U..."` をコピー・保存
6. Webhook URLはあとで空欄に戻してOK（プッシュ通知のみ使うため）

---

### 2. GitHubリポジトリの設定（5分）

#### 2-1. このフォルダをGitHubにプッシュ
```bash
git init
git add .
git commit -m "initial"
git remote add origin https://github.com/あなたのユーザー名/mlb-japanese-players.git
git push -u origin main
```

#### 2-2. GitHub Secretsに登録
GitHubのリポジトリページ → Settings → Secrets and variables → Actions → 「New repository secret」

| Name | Value |
|------|-------|
| `LINE_CHANNEL_ACCESS_TOKEN` | 1-2で取得したトークン |
| `LINE_USER_ID` | 1-3で取得したユーザーID（`Uxxxxxxxx...`） |

---

### 3. 動作確認

GitHubリポジトリの「Actions」タブ → 「MLB日本人選手 日次レポート」→ 「Run workflow」で手動実行できる。

---

## 日本語名の追加・更新

`ja_names.json` を編集するとLINEで表示される名前を変更できる。
選手IDの確認は以下を実行：

```bash
pip install requests
python discover_players.py
```

---

## 配信時間の変更

`.github/workflows/daily_report.yml` の `cron` を編集：

```yaml
- cron: '0 22 * * *'  # 22:00 UTC = 07:00 JST
```

UTC時間 = JST時間 − 9時間。例えば朝9時に変えたい場合は `0 0 * * *`（00:00 UTC = 09:00 JST）。
