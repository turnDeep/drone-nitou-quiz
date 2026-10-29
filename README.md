# ドローン二等学科 三択トレーニング

教則第五版の根拠を問題ごとに確認し、三択で学習するStreamlitアプリです。

**第1回50問・第2回50問の計100問を収録しています。** サイドバーの「問題集」で「第1回」「第2回」を選択できます。操作サンプルは削除しました。

提供写真の問題文・三択・正答・解説を、国土交通省の教則第五版と照合しました（2026年10月29日）。版改訂への対応に加え、原本の誤記や複数正解になり得る表現も修正し、元の表現と修正理由を保存しています。内訳と原文・修正文は、[第1回の照合結果](docs/question-audit.md)・[第2回の照合結果](docs/question-audit-round2.md)を参照してください。全問の解説は第五版を確認して学習用に書き直しています。

## できること

- 三つの選択肢から一つを選び、「回答する」で正解・不正解を表示
- 回答後に、正答、解説、教則第五版の根拠節・ページ・リンクを表示
- 解説の重要な語句を赤字と太字で表示
- 問題文の「誤っているもの」などの否定表現に下線を表示
- 白背景、枠付きの選択肢カード、選択時の青枠、水色の丸いボタン
- 選択肢を1つずつ独立したカードにし、問題文と選択肢は同じ文字サイズで表示
- 進捗と正答率、結果の確認、間違えた問題の復習
- 第1回・第2回の切り替え（各50問）と出題分野の絞り込み
- 第五版との照合が完了していない問題を出題対象から除外

学習履歴は接続中のセッション内で扱います。ブラウザーの再読み込みや接続の終了などで失われる場合があります。アカウントや永続保存はありません。

## Windowsで起動

Python 3.11を使用します。PowerShellから実行してください。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

表示された `http://localhost:8501` を開きます。初期表示は「第1回」で、サイドバーから「第2回」に切り替えられます。

## 検証

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

GitHub ActionsでもPython 3.11で同じテストを実行します。UIの動作テストと、問題データの形式・照合状態のテストは、写真の内容確認を代替しません。

現在の確認結果と未実施項目は[動作確認記録](docs/validation.md)にまとめています。

## 問題を追加する

1. 写真と正答・解説のページをそろえます。原本画像や一時作業ファイルはGit管理対象外です。今回の原本画像自体はGitHubへアップロードしていません。
2. [第五版への照合記録](docs/fifth-edition-review.md)の手順に沿って確認します。
3. [問題データのひな形](docs/question-template.json)を参考に、第1回は `data/questions.json`、第2回は `data/questions_round2.json` に追加します。ひな形の正答番号は仮置きなので、そのまま利用しないでください。
4. 照合完了後に `review.status` を `verified` にし、確認日と根拠節・ページを記録します。
5. テストと実画面で確認してからGitHubに反映します。

各問題ファイルの `original` に原文・元の正答・元の解説の要点、`audit` に修正理由を残しています。学習画面には正答理由と根拠ページを表示します。両回の照合一覧は次のコマンドで再生成できます。

```powershell
.\.venv\Scripts\python.exe scripts/update_review_report.py
```

## Streamlit Community Cloudへの配置

GitHubへの保存と、Community Cloudへのデプロイは別の作業です。

配置時は[Streamlit Community Cloud](https://share.streamlit.io/)にGitHubでログインし、Create appからリポジトリ `turnDeep/drone-nitou-quiz`、ブランチ `main`、エントリーポイント `app.py` を指定します。Pythonは3.11を選びます。非公開リポジトリへのアクセス許可と、アプリの閲覧権限を配置時に確認します。手順の詳細は[Streamlit公式ドキュメント](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app)を参照してください。

## 公式資料

- [国土交通省・無人航空機操縦者技能証明等](https://www.mlit.go.jp/koku/license.html)
- [無人航空機の飛行の安全に関する教則 第五版](https://www.mlit.go.jp/common/002010809.pdf)
- [第四版からの変更履歴](https://www.mlit.go.jp/common/002010810.pdf)

確認したPDFのURL・ページ数・SHA-256は[参照資料の記録](docs/sources.json)に保存しています。

第五版は2026年7月7日公布、2026年7月14日適用です。国土交通省は同日以降の学科試験が第五版準拠と案内しています（確認日：2026年10月29日）。このアプリは個人の学習用に作成するもので、国土交通省や試験機関の公式アプリではありません。

教則に基づく解説・照合記録は、国土交通省の公開資料を参照して編集・加工したものです。教則本文の利用条件は[国土交通省のリンク・著作権・免責事項](https://www.mlit.go.jp/link.html)を参照してください。
