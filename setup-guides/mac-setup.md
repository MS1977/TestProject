# Mac 環境メモ

**このファイルが正本。** 道具の使い方を変えたら、まずここを直す。

- `~/Documents` は iCloud 同期対象なので、iPhone の「ファイル」アプリからそのまま読める
- ブラウザ版（<https://claude.ai/code/artifact/53169fb1-9c4e-452d-834f-578e1622dea6> ）は
  **このファイルを公開したもの**。内容は同一で、更新も同じ URL に上書きされる
- 投資ノートとは別管理にしてある（`knowledge/` に置くと `kb_search.py` の索引に混ざるため）

各ツールの詳細はソース側にある。ここは横断的な使い方だけを置く。

> **担当: 日々の道具の使い方。**構築手順は [full-build-guide.md](full-build-guide.md) と各分野の文書、
> 今の版やパスは [dev-environment-map.md](dev-environment-map.md) を見る。

🛑 **自作アプリの使い方はここには書かない。**仕様の正本は
**`~/Documents/Developer/App/`** にまとめてある（二重に持つと必ず食い違う）。

| アプリ | 何をするか | 仕様の正本 |
| --- | --- | --- |
| **AutoScroll** | Safari の自動スクロール＋自動ページ送り | `Documents/Developer/App/AutoScroll.md` |
| **PageCapture** | Safari のページ全体を 1 枚の PNG に | `Documents/Developer/App/PageCapture.md` |
| **PageShot** | ← / → で最前面ウィンドウを撮る＋OCR | `Documents/Developer/App/PageShot.md` |

---

## 1. Xcode ビルド支援（Claude Code）

Apple 純正 MCP（`xcrun mcpbridge`）と、経路を振り分けるスキルを入れてある。
iOS 限定ではなく macOS・Safari 拡張・Swift Package でも動く。

「ビルドして」「テスト走らせて」と言うだけでよい。

| 経路 | いつ | 特徴 |
| --- | --- | --- |
| MCP | Xcode 起動中・スキーム指定なし | Xcode の現在設定でビルド。速い |
| CLI | Xcode 未起動・スキーム指定あり・SPM | サブエージェントが実行。ログは隔離 |

MCP でしかできないこと: SwiftUI プレビュー描画 / Apple ドキュメント検索 / Swift スニペット実行。

> **`mcpbridge` は Xcode が起動していないと即死する。**
> `Connection closed` が出たらこれ。順序は **Xcode 起動 → プロジェクトを開く → Claude Code 起動**。

中身: `~/.claude/skills/xcode-build/` ／ `~/.claude/agents/xcode-{build,test}-runner.md`

---

## 2. 長文の下処理（ローカル LLM）

3 万字の文字起こしを 1 割前後に圧縮してから読む。LM Studio の `google/gemma-3-12b` を使う。

```bash
cd ~/Documents/knowledge/scripts && ./run_digest_bg.sh --all --unload
```

バックグラウンドで動き、Claude を閉じても止まらない。処理中はスリープも抑止する。
`--unload` は終了後にメモリ 8GB を解放する指定。

| 用途 | コマンド |
| --- | --- |
| 進捗 | `tail -f ~/Documents/knowledge/out/llm_digest.log` |
| 稼働確認 | `pgrep -lf llm_digest.py` |
| 停止 | `pkill -f llm_digest.py` |

途中で止めても安全。処理済みは飛ばすので、再実行すれば続きから。

出力は `youtube/<名前>.digest.md`。見出しは「要点 / 数値・パラメータ / 銘柄・通貨ペア・指標・手法名 /
主張とその根拠」。**「根拠の提示なし」が並ぶ動画は取り込む価値が薄い**、という足切りに使える。

実績: 8 件で 221,070 字 → 30,115 字（13.6%）。

> ⚠️ **LLM に事実を持たせない。**12B は日付や数値を取り違える。
> 数字はスクリプトで機械的に抽出し、LLM には言語化だけさせる。OCR にも生成モデルは使わない（4 節）。
> この原則の正本はここ。

> **ダイジェストを根拠に売買判断をしない。**
> 12B なので数値の取り違えが起きる。食い違いには `※要確認` が付くが完全ではなく、
> 文字起こしの誤変換（「ダウリドンの意識」= ダウ理論）は素通りする。検証対象は常に原文の `.txt`。

---

## 3. KB の意味検索

キーワードが一致しなくても、意味が近いメモを拾う。ベクトル DB は使わない。

```bash
cd ~/Documents/knowledge/scripts
python3 kb_search.py "順張りの出口はどうすべきか"
python3 kb_search.py "増資の影響" --dir stocks -n 10
python3 kb_search.py --index          # メモを足したら実行（差分のみ・数秒）
```

**固有名詞（銘柄コード・手法名・指数名）を 1 語混ぜるのが最も効く。**

| 聞き方 | 結果 |
| --- | --- |
| `"6857 アドバンテスト"` | ◎ 単元345万円で買えない、を的中 |
| `"TOPIX 地合い 判定"` | ◎ 0.883 |
| `"地合いの判定にはどの指数を見るべきか"` | △ 抽象的すぎると平坦 |

上位のスコア差が小さいと「決め手のある一致がありません」と警告が出る。

現在 2879 チャンク / 9.1MB。

---

## 4. 画面を撮ってテキストにする

紙・電子書籍・資料を、ページ送りしながら撮り、まとめて文字に起こす経路。

```
PageShot（← / → でページを撮る）      ← 仕様は App/PageShot.md
  → ocr-folder（テキスト化）
  → llm_digest（長ければ圧縮）
  → kb_search / kb_ask（引く）
```

ここに書くのは **`ocr-folder`（ターミナルの道具）だけ**。撮る側は App/PageShot.md を見る。

### ocr-folder — 画像フォルダを文字に起こす

```bash
ocr-folder ~/Desktop/撮影フォルダ      # 隣に 撮影フォルダ.md ができる
ocr-folder <フォルダ> --separate       # 画像ごとに .txt
ocr-folder <フォルダ> --out 本.md --recursive
```

**エンジンは 2 つあり、既定は自動選択。**生成モデル（VLM）は使わない——
意味から勝手に補完してしまい、数字を静かに書き換えるため。

|  | Vision（macOS 内蔵） | Tesseract 5.5.3 | gemma-3-12b (VLM) |
| --- | --- | --- | --- |
| 用途 | **横組み** | **縦組み（縦書き）** | 使わない |
| 所要 | **0.87 秒/枚** | 数秒/枚 | 15 秒/枚 |
| メモリ | ほぼゼロ | ほぼゼロ | 8 GB |
| 精度 | 横組みは全文正確 | 縦組みを読める唯一の手 | 「日経平均」→「経済平均」等の誤り |

> 🛑 **Vision は縦組みの日本語を 1 文字も読めない。**
> revision を変えても、回転させても、切り出しても読めない（2026-08 に実測して確定）。
> 縦書きの本を Vision に通すと**空のテキストが出てくる**——エラーにならないので気づきにくい。
> Tesseract に `-l jpn_vert --psm 5` で渡すと読める。**同じ本で 4,883 字 → 72,304 字。**

> ⚠️ **ただし Tesseract は数字を間違える。**本文は読めても、株価・年月日・パーセントは
> **必ず元画像と突き合わせる。**

自動は本文の向きを見て振り分ける。**段組み（2 段組の縦書き）も列を検出して順序を復元する。**

> **本1冊を通す前に、最初の数ページで精度を確認する。**
> フォントによって読み落としが出る。装飾記号（`- 1 -` のページ番号など）は特に弱い。

## 5. Remote Control（iPhone から Mac を操作）

```bash
~/bin/remote-control.sh
```

`nohup` で切り離して起動するので、ターミナルを閉じても切れない。
接続すると iPhone の Claude アプリ / <https://claude.ai/code> から、この Mac のセッションを
見て操作できる。通知もスマホに飛ぶようになる。

| 用途 | コマンド |
| --- | --- |
| 稼働確認 | `pgrep -lf "claude remote-control"` |
| ログ | `tail -f ~/.claude/remote-control.log` |
| 停止 | `pkill -f "claude remote-control"` |

**Mac がスリープすると切れる**（`caffeinate` は掛けていない）。

### 401 や API キー認証で弾かれたら

原因と対処（`ANTHROPIC_API_KEY` との衝突、OAuth の失効、Keychain での確認方法）は
[xcode-claude-setup.md](xcode-claude-setup.md) の 3 節。

この Mac での経緯:

1. `~/.zshrc` の `ANTHROPIC_API_KEY` をコメントアウト（バックアップ `~/.zshrc.bak-20260815`）
2. 2026-06-15 に期限切れしていた OAuth を `claude auth logout` → `login` で再取得
3. **2026-09-01 平文のキーごと `.zshrc` から削除し、キー自体も失効させた。**
   現在は該当行が無い（`grep ANTHROPIC_API_KEY ~/.zshrc` は何も返さない）

---

## 6. セッション間の情報共有

| 仕組み | 用途 |
| --- | --- |
| メモリ（40 件） | 毎セッション自動で読まれる。検証で分かった結論を置く |
| 過去セッションの全文検索 | 「あの話どのセッション？」が引ける |
| `CLAUDE.md` | そのフォルダで作業する時に必ず適用されるルール |
| iCloud | `~/Documents` は同期対象。iPhone の「ファイル」アプリで読める |
| Remote Control | セッションそのものを iPhone から操作 |

`CLAUDE.md` の場所: `~/Documents/knowledge/` ／ `~/Documents/Developer/SafariAutoScroll/` ／ `~/Documents/Developer/PageCapture/`

---

## 7. 自動で動くもの・セキュリティ

### ログイン時の自動起動

`~/bin/tv-claude.command` を**ログイン項目**に登録してある。ログインすると

1. TradingView を `--remote-debugging-port=9222` 付きで起動する（MCP がこのポートを使う）
2. ポートが開くのを最大 15 秒待つ
3. 続けて `claude` を Terminal で起動する

```bash
~/bin/tv-claude.command --check   # claude を起動せず、ポートの状態だけ見る
```

> **なぜ launchd ではないか。**`claude` は対話プログラムなので端末が要り、
> さらに launchd から起動したプロセスは TCC により `~/Documents` を読み書きできない。
> 投資 KB を触れないと意味がないので、`.command` ＋ Terminal 経由にしている。

> ⚠️ **通常起動した TradingView には後からポートを付けられない。**
> Dock から起動していると `--check` が警告を出す。いったん終了してから実行し直す。

### 常駐の仕掛けの監視

```bash
python3 ~/bin/malware-check.py        # 前回との差分だけ（毎日10:10に自動実行）
python3 ~/bin/malware-check.py --full # 現在の全項目
```

LaunchAgent / LaunchDaemon・ログイン項目・構成プロファイル・kext・`/etc/hosts`・
アドウェアの常用領域・Safari 拡張を毎日棚卸しし、**前回から変わった行だけ**を出す。
変化がなければ 1 行で終わる。現在 16 件。詳細は
[dev-environment-map.md](dev-environment-map.md) の 8 節。

> 🛑 **`--baseline` は本人だけが打つ。**「今の状態を正常として承認する」操作で、
> Claude に打たせると検知した脅威をそのまま飲み込む。

> ⚠️ 見ているのは**既知の常駐経路の変化だけ**。**「変化なし」は「感染していない」ではない。**

---

## 困ったとき

| 症状 | やること |
| --- | --- |
| MCP が `Connection closed` | Xcode を起動する。順序は Xcode → Claude Code |
| 下処理が進まない | `~/.lmstudio/bin/lms server start` → モデルのロードも要る |
| メモリが足りない | `~/.lmstudio/bin/lms unload --all` で 8GB 戻る |
| OCR の精度が低い | 撮影解像度を上げる。装飾記号や特殊フォントは苦手なので、本文だけ拾えているか確認 |
| Remote Control が 401 | `claude auth logout` → `claude auth login`（ブラウザで完走させる） |
| Safari の拡張がおかしい | `Documents/Developer/App/` の仕様書を見る（ここには書かない） |
| 縦書きの本を OCR したら**空**だった | Vision は縦組みを読めない。エンジンを Tesseract に切り替える |
| OCR の数字が本と違う | Tesseract は数字を外す。**元画像と突き合わせる**。他は信用してよい |
| TradingView の MCP が繋がらない | ポート 9222 が開いていない。`~/bin/tv-claude.command --check` |
| 常駐チェックが 🔴 を出し続ける | 仕様。中身を確かめて問題なければ `malware-check.py --baseline` |

---

## 関連ドキュメント

各話題の正本は 1 か所だけ。他の文書には要点 1 行とリンクだけを置く。

| ドキュメント | 担当（ここが正本） | ブラウザ版 |
| --- | --- | --- |
| [full-build-guide.md](full-build-guide.md) | 組む順番・関門・全体の検証・横断の早見表 | [開く](https://claude.ai/artifact/UQ2CnYtdPN3hYV7owG4wZQ) |
| [dev-environment-map.md](dev-environment-map.md) | 今の状態（実測値・版・パス・常駐物・ディレクトリ） | [開く](https://claude.ai/artifact/2rFMQREMuY9xioDRpGfjkE) |
| [eclipse-spring-setup.md](eclipse-spring-setup.md) | Java・Spring Boot・MyBatis・PostgreSQL | [開く](https://claude.ai/artifact/Y41hjzjgRYfb6UDYuTBs8J) |
| [xcode-claude-setup.md](xcode-claude-setup.md) | Xcode・署名・ビルド成果物・Claude Code 認証・MCP | [開く](https://claude.ai/artifact/Xu6T46zjyfxDUZKq44aS83) |
| [mac-setup.md](mac-setup.md) | 日々の道具の使い方（LLM 下処理・KB 検索・OCR・Remote Control・自動起動・常駐監視） | [開く](https://claude.ai/artifact/BG5zw9e2TpgDdwRU4NCV5f) |
