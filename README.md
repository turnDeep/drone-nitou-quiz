# ドローン二等学科 三択トレーニング

教則第五版の根拠を問題ごとに確認し、三択で学習するStreamlitアプリです。

**現在は写真の受領待ちです。写真から取り込んだ問題は0件で、問題集の第五版適合確認は未実施です。** アプリの操作確認用に独自作成した2問を別モードで用意しています。写真の問題を照合済みと扱ったり、第五版の全範囲を網羅した問題集として提供したりするものではありません。

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

表示された `http://localhost:8501` を開きます。「操作サンプル」モードで動作を確認できます。

## 検証

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

GitHub ActionsでもPython 3.11で同じテストを実行します。UIの動作テストと、問題データの形式・照合状態のテストは、写真の内容確認を代替しません。

現在の確認結果と未実施項目は[動作確認記録](docs/validation.md)にまとめています。

## 問題を追加する

1. 写真と正答・解説のページをそろえます。原本画像の保存先 `inputs/` はGit管理対象外です。
2. [第五版への照合記録](docs/fifth-edition-review.md)の手順に沿って確認します。
3. [問題データのひな形](docs/question-template.json)を参考に `data/questions.json` に追加します。ひな形の正答番号は仮置きなので、そのまま利用しないでください。
4. 照合完了後に `review.status` を `verified` にし、確認日と根拠節・ページを記録します。
5. テストと実画面で確認してからGitHubに反映します。

## Streamlit Community Cloudへの配置

GitHubへの保存と、Community Cloudへのデプロイは別の作業です。現在、Community Cloudへのデプロイはしていません。

写真の問題の照合と取り込みが完了したら、[Streamlit Community Cloud](https://share.streamlit.io/)にGitHubでログインし、Create appからこのリポジトリ、ブランチ `main`、エントリーポイント `app.py` を指定します。Pythonは3.11を選びます。非公開リポジトリへのアクセス許可と、アプリの閲覧権限を配置時に確認します。手順の詳細は[Streamlit公式ドキュメント](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app)を参照してください。

## 公式資料

- [国土交通省・無人航空機操縦者技能証明等](https://www.mlit.go.jp/koku/license.html)
- [無人航空機の飛行の安全に関する教則 第五版](https://www.mlit.go.jp/common/002010809.pdf)
- [第四版からの変更履歴](https://www.mlit.go.jp/common/002010810.pdf)

確認したPDFのURL・ページ数・SHA-256は[参照資料の記録](docs/sources.json)に保存しています。

第五版は2026年7月7日公布、2026年7月14日適用です。国土交通省は同日以降の学科試験が第五版準拠と案内しています（確認日：2026年10月29日）。このアプリは個人の学習用に作成するもので、国土交通省や試験機関の公式アプリではありません。
