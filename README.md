# ドローン二等学科 三択トレーニング

教則第五版の根拠を問題ごとに確認し、三択で学習するStreamlitアプリです。

**提供写真20枚にある第1回の全50問を取り込み、問題文・三択・正答・解説を教則第五版の該当本文と照合しました（2026年10月29日）。** 初期表示の「写真の問題」で学習できます。操作確認用の独自2問も別モードに残しています。

原本の正答位置は全50問で維持していますが、原本のままでは複数の選択肢を正しいと読める問題や限定条件が不足した問題など、**14問の設問・選択肢を修正**しました。ほか**11問の解説に条件や注意点を補足**し、25問は正答・設問を維持しています。全問の解説は第五版を参照して学習用に書き直しました。内訳と原文・修正文は[50問の照合結果](docs/question-audit.md)を参照してください。これらは提供された50問の確認であり、第五版の全範囲を網羅する問題集ではありません。

## できること

- 三つの選択肢から一つを選び、「回答する」で正解・不正解を表示
- 回答後に、正答、解説、教則第五版の根拠節・ページ・リンクを表示
- 進捗と正答率、結果の確認、間違えた問題の復習
- 写真の問題と操作サンプルの切り替え
- 第五版との照合が完了していない問題を出題対象から除外

学習履歴は接続中のセッション内で扱います。ブラウザーの再読み込みや接続の終了などで失われる場合があります。アカウントや永続保存はありません。

## Windowsで起動

Python 3.11を使用します。PowerShellから実行してください。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

表示された `http://localhost:8501` を開きます。「写真の問題」モードで50問を学習できます。

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
3. [問題データのひな形](docs/question-template.json)を参考に `data/questions.json` に追加します。ひな形の正答番号は仮置きなので、そのまま利用しないでください。
4. 照合完了後に `review.status` を `verified` にし、確認日と根拠節・ページを記録します。
5. テストと実画面で確認してからGitHubに反映します。

`data/questions.json` の `original` に原文・元の正答・元の解説の要点、`audit` に修正理由を残しています。学習画面には正答理由と根拠ページを表示します。照合一覧は次のコマンドで再生成できます。

```powershell
.\.venv\Scripts\python.exe scripts/update_review_report.py
```

## Streamlit Community Cloudへの配置

GitHubへの保存と、Community Cloudへのデプロイは別の作業です。現在、Community Cloudへのデプロイはしていません。

配置時は[Streamlit Community Cloud](https://share.streamlit.io/)にGitHubでログインし、Create appからリポジトリ `turnDeep/drone-nitou-quiz`、ブランチ `main`、エントリーポイント `app.py` を指定します。Pythonは3.11を選びます。非公開リポジトリへのアクセス許可と、アプリの閲覧権限を配置時に確認します。手順の詳細は[Streamlit公式ドキュメント](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app)を参照してください。

## 公式資料

- [国土交通省・無人航空機操縦者技能証明等](https://www.mlit.go.jp/koku/license.html)
- [無人航空機の飛行の安全に関する教則 第五版](https://www.mlit.go.jp/common/002010809.pdf)
- [第四版からの変更履歴](https://www.mlit.go.jp/common/002010810.pdf)

確認したPDFのURL・ページ数・SHA-256は[参照資料の記録](docs/sources.json)に保存しています。

第五版は2026年7月7日公布、2026年7月14日適用です。国土交通省は同日以降の学科試験が第五版準拠と案内しています（確認日：2026年10月29日）。このアプリは個人の学習用に作成するもので、国土交通省や試験機関の公式アプリではありません。

教則に基づく解説・照合記録は、国土交通省の公開資料を参照して編集・加工したものです。教則本文の利用条件は[国土交通省のリンク・著作権・免責事項](https://www.mlit.go.jp/link.html)を参照してください。
