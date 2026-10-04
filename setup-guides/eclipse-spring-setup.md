# Eclipse × Spring Boot × MyBatis × PostgreSQL 構築記録

2026-08-22 に構築した内容。**実際に踏んだ問題と、その解決をそのまま残してある。**

検証環境: MacBook Pro (M1 Pro / 16GB) / macOS 26.6 /
Pleiades All in One Eclipse 2026-06 / PostgreSQL 17.11

> **担当: Java・Spring Boot・MyBatis・PostgreSQL の構築と知見。**
> PostgreSQL の導入・接続確認・pgAdmin・`pg_hba.conf` はこの文書が正本。
> 今の版や接続先の実測値は [dev-environment-map.md](dev-environment-map.md) を見る。

---

## 到達点

```
Spring Boot 4.0.8 + MyBatis 4.0.1 + PostgreSQL 17.11
→ http://localhost:8080/actuator/health が {"status":"UP"} を返す
→ db コンポーネントも UP（PostgreSQL との疎通も同時に確認できる）
→ t_sandbox に対する CRUD が /api/sandbox で動く（Mapper + Controller）
```

| 対象 | 場所・値 |
| --- | --- |
| プロジェクト | `~/Documents/Developer/spring-mybatis-sandbox`（2026-09-01 に `~/Developer` から移動） |
| Eclipse | `/Applications/Eclipse_2026-06.app`（Pleiades） |
| PostgreSQL | `/opt/homebrew/var/postgresql@17`（Homebrew・自動起動） |
| DB / ユーザー | `sandbox` / `sandbox`（パスワード `sandbox`） |
| GUI クライアント | `/Applications/pgAdmin 4.app`（9.17） |
| Maven キャッシュ | `~/.m2/repository`（約 120MB） |

---

## 1. Eclipse（Pleiades）

### 起動できない — Gatekeeper に弾かれる

初回起動時に「開いていません／マルウェアが含まれていないか検証できませんでした」
と出て、**「開く」ボタンが無い**（ゴミ箱に入れる／完了のみ）。

原因は Pleiades が **Apple の公証（notarization）を受けていない**こと。
署名は `pleiades-cert`（自己署名）で `TeamIdentifier` が未設定。

```bash
codesign -dv --verbose=2 /Applications/Eclipse_2026-06.app 2>&1 | grep Authority
# → Authority=pleiades-cert
spctl -a -vvv -t exec /Applications/Eclipse_2026-06.app
# → rejected
```

**対処**（公式サイトから取得したものであることを確認してから）:

```bash
sudo xattr -dr com.apple.quarantine /Applications/Eclipse_2026-06.app
```

`-r` は中のファイルまで再帰的に外す指定。Eclipse は内部に多数の実行ファイルを
持つのでこれが要る。

> マルウェアだから弾かれたのではなく、**Apple に検証されていない**ため。
> 公証済みの本家 Eclipse（eclipse.org）ならこの問題は起きない。

### 同梱されているもの

Pleiades は JDK と Maven を同梱している。**別途インストールは不要。**

| 種類 | 内容 |
| --- | --- |
| JDK | **8 / 11 / 17 / 21 / 25**（`Contents/java/` 配下） |
| Maven | m2e に内蔵（3.9.16） |

Eclipse 自身は `eclipse.ini` の `-vm` で **JDK 21** を使って起動する。

> **`java` や `mvn` はターミナルからは使えない。**JDK は Eclipse の中にしか無く、
> PATH には入っていない。CLI で使うなら `JAVA_HOME` を明示するか、
> 別途 Homebrew などで入れる。
>
> ```bash
> export JAVA_HOME=/Applications/Eclipse_2026-06.app/Contents/java/21
> export PATH="$JAVA_HOME/bin:$PATH"
> ```

---

## 2. PostgreSQL

### Docker ではなく Homebrew を選んだ

構築時のメモリ空きが **0.1GB / 16GB** だった。Docker Desktop は起動に約 2GB 要る。
Homebrew 版は常駐が軽いため、こちらを選択。

再現性やチーム共有を重視するなら Docker のほうが向く。**メモリに余裕があるかで決める。**

### 導入

```bash
brew install postgresql@17
brew services start postgresql@17
```

インストール時に**データベースクラスタが自動作成される**
（`initdb --locale=en_US.UTF-8 -E UTF-8 /opt/homebrew/var/postgresql@17`）。

`postgresql@17` は keg-only なので PATH を通す。

```bash
export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"   # ~/.zshrc に追記済み
```

> 追記した直後の既存ターミナルでは効かない。`rehash` するか新しいタブを開く。

### 開発用の DB とユーザー

```sql
CREATE ROLE sandbox WITH LOGIN PASSWORD 'sandbox';
CREATE DATABASE sandbox OWNER sandbox;
```

```bash
psql -d postgres -c "CREATE ROLE sandbox WITH LOGIN PASSWORD 'sandbox';"
psql -d postgres -c "CREATE DATABASE sandbox OWNER sandbox;"
```

確認:

```bash
PGPASSWORD=sandbox psql -h localhost -U sandbox -d sandbox -c "SELECT current_user;"
```

> **`-h localhost` を付けて確認すること。** 付けないと UNIX ソケット経由になり、
> アプリ（JDBC）が使う TCP 経路の確認にならない。実際にこれで見落として、
> 「psql では繋がるのにアプリからは Connection refused」になった。

### 運用

```bash
brew services list                    # 状態
brew services restart postgresql@17   # 再起動
brew services stop postgresql@17      # 停止
```

ログ: `/opt/homebrew/var/log/postgresql@17.log`

> 構築中、一度サービスが `smart shutdown` を受けて停止していた（クラッシュではない）。
> 接続できなくなったら **まず `brew services list` で `started` か確認**する。

### GUI で中身を見る — pgAdmin 4

`/Applications/pgAdmin 4.app`（9.17）を使う。CLI の `psql` と同じ DB を、
テーブル一覧・データ編集・クエリ結果のグリッド表示で扱える。

「Let's connect to the server」の入力値:

| 項目 | 値 |
| --- | --- |
| Existing Server (Optional) | 空のまま |
| **Server Name** | `Local sandbox`（**任意の表示名**） |
| Host name/address | `localhost` |
| Port | `5432` |
| Database | `sandbox` |
| User | `sandbox` |
| Password | `sandbox` |
| Role / Service | 空 |
| Connection Parameters | 既定のまま（`sslmode=prefer` / `connect_timeout=10`） |

> **`'Server Name' cannot be empty.` で弾かれるのは接続失敗ではない。**
> Server Name は pgAdmin 上の**表示ラベル**で、接続先とは無関係。何か入れれば通る。
> 接続先を決めているのは Host / Port / Database の 3 つ。

テーブル作成やロール管理をするなら、管理者ロールで入る。

| 項目 | 値 |
| --- | --- |
| User | `shibuyamorishige`（＝ macOS のユーザー名） |
| Database | `postgres` |
| Password | 空でよい（下記） |

### ⚠️ ローカル接続は `trust`（パスワード不要）

Homebrew 版の既定では `pg_hba.conf` がこうなっている。

```
host    all    all    127.0.0.1/32    trust
host    all    all    ::1/128         trust
```

`trust` は**無条件許可**。このマシンで動くプロセスは、パスワードなしで
**管理者ロールを含む任意のユーザーとして接続できる**。開発機なので実害は小さいが、
把握しておく。締めるなら:

```bash
# hba_file の場所を出す
psql -d postgres -tAc "SHOW hba_file;"
# → 上記2行の trust を scram-sha-256 に書き換えてから
brew services restart postgresql@17
```

---

## 3. バージョンの決定（ここが一番苦労した）

### Spring Initializr は 3.x を受け付けない

```
Invalid Spring Boot version '3.4.7',
Spring Boot compatibility range is >=4.0.0
```

2026-08 時点で Initializr が生成できるのは **4.0.0 以上のみ**。

### MyBatis の対応版を突き止める

`search.maven.org` の検索 API では `mybatis-spring-boot-starter` の最新が
**3.0.4 としか出ず、4.x が見つからなかった**。

だが実際には存在した。リポジトリの URL を直接叩けば確認できる。

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  https://repo1.maven.org/maven2/org/mybatis/spring/boot/mybatis-spring-boot-starter/4.0.1/mybatis-spring-boot-starter-4.0.1.pom
# → 200
```

> **検索 API の結果だけで「無い」と判断しない。**リポジトリを直接見る。

確定した組み合わせ:

| ライブラリ | 版 | 前提 |
| --- | --- | --- |
| Spring Boot | 4.0.8 | Java **17** 以上 |
| mybatis-spring-boot-starter | 4.0.1 | Spring Boot 4.0.1 |
| postgresql (JDBC) | 42.7.13 |  |
| Java | **21**（Eclipse 同梱の LTS） |  |

---

## 4. プロジェクト生成

```bash
curl -o starter.zip "https://start.spring.io/starter.zip\
?type=maven-project&language=java&bootVersion=4.0.8.RELEASE&javaVersion=21\
&groupId=com.example&artifactId=sandbox&name=sandbox&packageName=com.example.sandbox\
&dependencies=web,mybatis,h2,postgresql,lombok"
```

### ⚠️ 生成された pom がそのままでは通らない

親 POM のバージョンが **`4.0.8.RELEASE`** と書き出されるが、
Maven Central にあるのは **`4.0.8`**（`.RELEASE` 付きは 404）。

```
Non-resolvable parent POM: org.springframework.boot:spring-boot-starter-parent:...
```

**対処**: `pom.xml` の parent の version から `.RELEASE` を削る。

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>4.0.8</version>
</parent>
```

> **Initializr が生成したものが即ビルドできるとは限らない。**

---

## 5. 依存の一括取得

回線の良いときにまとめて取る。**約 120MB。**

```bash
cd ~/Documents/Developer/spring-mybatis-sandbox
export JAVA_HOME=/Applications/Eclipse_2026-06.app/Contents/java/21
export PATH="$JAVA_HOME/bin:$PATH"
./mvnw -B test
```

`mvnw`（Maven Wrapper）が Maven 本体も自動で取得するので、**`brew install maven` は不要。**

### ⚠️ `dependency:go-offline` だけでは足りない

「一括取得」の定番コマンドだが、**テスト実行時にしか使わないプラグインは取得されない。**
実際、オフラインでビルドしたら次で落ちた。

```
Cannot access central in offline mode and the artifact
org.apache.maven.surefire:surefire-junit-platform:jar:3.5.6 has not been downloaded
```

**`./mvnw test` まで通しておく**のが確実。完全にオフラインで動くかは次で検証できる。

```bash
./mvnw -B -o clean test     # -o = オフライン
```

---

## 6. 設定

### src/main/resources/application.properties

```properties
spring.application.name=sandbox

# PostgreSQL
spring.datasource.url=jdbc:postgresql://localhost:5432/sandbox
spring.datasource.username=sandbox
spring.datasource.password=sandbox
spring.datasource.driver-class-name=org.postgresql.Driver

# MyBatis
mybatis.mapper-locations=classpath:mapper/*.xml
mybatis.configuration.map-underscore-to-camel-case=true

# Actuator（動作確認用）
management.endpoints.web.exposure.include=health,info
management.endpoint.health.show-details=always
```

`map-underscore-to-camel-case` は、DB の `user_name` を Java の `userName` に
自動で対応づける設定。MyBatis を使うならほぼ必ず入れる。

> **actuator は公開範囲を絞る。**既定では多くの情報を出せる。
> `show-details=always` も開発用で、本番では `when-authorized` などにする。

---

## 7. Eclipse へのインポート

1. **File → Import…**
2. **Maven → Existing Maven Projects**
3. Root Directory に `/Users/<名前>/Documents/Developer/spring-mybatis-sandbox`
4. `pom.xml` にチェックして **Finish**

依存が取得済みなら数十秒で終わる。`.project` `.classpath` は m2e が生成する。

`pom.xml` を変更したら **右クリック → Maven → Update Project** で反映する。

### 実行

`SandboxApplication.java` を右クリック → **Run As → Java Application**

---

## 8. 起動の確認

```
http://localhost:8080/actuator/health
```

```json
{
  "status": "UP",
  "components": {
    "db": { "status": "UP", "details": { "database": "PostgreSQL" } },
    "diskSpace": { "status": "UP" },
    "ping": { "status": "UP" }
  }
}
```

**`status: UP` かつ `db` が UP なら、アプリと DB の両方が正常。**

コントローラを作っていない段階では `http://localhost:8080/` は **404**（Whitelabel Error Page）
になるが、これは**サーバーが動いている証拠**。接続拒否とは違う。

---

## 9. MyBatis の Mapper を書く

対象テーブル（pgAdmin で作成）:

```sql
CREATE TABLE t_sandbox (
    id          numeric(14,0) NOT NULL PRIMARY KEY
                DEFAULT nextval('t_sandbox_id_seq'),   -- 後から付けた（後述）
    name        varchar(120),
    code        char(4),
    image       bytea,
    memo        text,
    insert_date timestamptz,
    update_date timestamptz
);
```

### 3 つのファイルが名前で結びついている

MyBatis は「実装を書かないインタフェース」と「SQL を書いた XML」を、
**名前の一致だけ**で繋ぐ。ここが唯一にして最大のハマりどころ。

```
SandboxMapper.java          @Mapper interface SandboxMapper
  ↕ namespace が完全修飾名と一致
SandboxMapper.xml           <mapper namespace="com.example.sandbox.mapper.SandboxMapper">
  ↕ id がメソッド名と一致
                            <select id="findById" ...>
  ↕ 場所は properties が決める
application.properties      mybatis.mapper-locations=classpath:mapper/*.xml
```

ずれると起動時に `Invalid bound statement (not found)` で落ちる。
**この例外が出たら、まず namespace とメソッド名の綴りを疑う。**

### 作ったファイル

| ファイル | 役割 |
| --- | --- |
| `domain/Sandbox.java` | 1 行を表す。Lombok の `@Data` |
| `mapper/SandboxMapper.java` | メソッド定義のみ。`@Mapper` |
| `resources/mapper/SandboxMapper.xml` | SQL 本体 |
| `web/SandboxController.java` | REST エンドポイント |
| `test/SandboxMapperTest.java` | 実 DB に対するテスト |

> Mapper が増えたら、各クラスの `@Mapper` の代わりに起動クラスへ
> `@MapperScan("com.example.sandbox.mapper")` を付ける手もある。

### 列の型で気をつけた点

| 列 | 型 | 注意 |
| --- | --- | --- |
| `id` | `numeric(14,0)` | `long` の範囲に収まる（10^14 < 9.2×10^18）ので `Long` で受ける。採番は DB 側 |
| `code` | **`char(4)`** | **固定長。空白で右詰めされる。**`"AB"` を入れて読むと `"AB  "` |
| `image` | `bytea` | `byte[]`。一覧の SELECT では取得しない（重いため） |
| `insert_date` | `timestamptz` | `OffsetDateTime`。値は SQL 側の `now()` |

`insert_date` → `insertDate` の変換は
`mybatis.configuration.map-underscore-to-camel-case=true` が効いている。
**この設定があるので `resultMap` は書かなくていい。**

### id の採番はシーケンスに任せる

作成直後の `t_sandbox` には `identity` も `sequence` も無く、INSERT 時に id を
渡す必要があった。**アプリ側で `SELECT MAX(id)+1` するのは競合に弱い**
（同時リクエストが同じ値を引いて PK 重複になる）ので、DB 側に持たせる。

```sql
CREATE SEQUENCE t_sandbox_id_seq OWNED BY t_sandbox.id;
ALTER TABLE t_sandbox ALTER COLUMN id SET DEFAULT nextval('t_sandbox_id_seq');
```

`OWNED BY` を付けると、**テーブルを DROP したときシーケンスも一緒に消える。**
付けないと孤児が残る。

アプリ側は id を INSERT 文から外し、採番結果を受け取る指定を足す。

```xml
<insert id="insert" parameterType="com.example.sandbox.domain.Sandbox"
        useGeneratedKeys="true" keyColumn="id" keyProperty="id">
    INSERT INTO t_sandbox (name, code, image, memo, insert_date, update_date)
    VALUES (#{name}, #{code}, #{image}, #{memo}, now(), now())
</insert>
```

| 属性 | 意味 |
| --- | --- |
| `useGeneratedKeys="true"` | JDBC の `getGeneratedKeys()` で採番結果を受け取る |
| `keyColumn="id"` | その中のどの列を読むか |
| `keyProperty="id"` | 読んだ値を引数オブジェクトのどこへ入れるか |

**戻り値は id ではなく件数。**採番された id は `insert()` を呼んだ後の
**引数オブジェクト**から読む。

```java
mapper.insert(body);      // 戻り値は 1（件数）
body.getId();             // ← ここに採番結果が入っている
```

> **シーケンスはロールバックされない。**テストを `@Transactional` で巻き戻しても
> 消費した番号は戻らないため、**id には歯抜けができる。**これは PostgreSQL の
> 仕様（同時実行のため意図的にトランザクション外で動く）で、異常ではない。
> 実際、テスト実行後に POST したら id は 1 ではなく **8 から始まった。**

### 部分更新は `<set>` + `<if>` で書く

送られなかった項目を消さないための定番。

```xml
<update id="update">
    UPDATE t_sandbox
    <set>
        <if test="name != null">name = #{name},</if>
        <if test="memo != null">memo = #{memo},</if>
        update_date = now()
    </set>
    WHERE id = #{id}
</update>
```

`<set>` は末尾に余ったカンマを自動で取り除く。

> **値の埋め込みは必ず `#{...}`。**これは PreparedStatement のプレースホルダになる。
> `${...}` は文字列をそのまま連結するので、値に使うと SQL インジェクションになる。

### テストは実 DB に対して書く

```java
@SpringBootTest
@Transactional          // ← 各テスト後に必ずロールバックされる
class SandboxMapperTest { ... }
```

`@Transactional` をテストクラスに付けると Spring が毎回ロールバックする。
**実物の PostgreSQL を使いながらデータが残らない。**

H2 に差し替える手もあるが、`char(4)` の空白詰めや `numeric` の扱いは
DB ごとに違う。**型の振る舞いを取りこぼさないので実 DB を勧める。**

```bash
./mvnw -B test
# → Tests run: 7, Failures: 0, Errors: 0  (SandboxMapperTest)
```

### 動作確認

```bash
./mvnw spring-boot:run
```

```bash
curl -X POST http://localhost:8080/api/sandbox \
  -H 'Content-Type: application/json' \
  -d '{"name":"最初の1件","code":"AB","memo":"テスト"}'
```

```json
{
  "id": 8,
  "name": "最初の1件",
  "code": "AB  ",
  "memo": "テスト",
  "insertDate": "2026-08-22T08:08:47.984983Z",
  "updateDate": "2026-08-22T08:08:47.984983Z"
}
```

**実測値。**2 点とも仕様どおりの挙動。

- `code` が `"AB  "` ＝ `char(4)` の空白詰め
- `id` が 1 でなく 8 ＝ テストで消費したシーケンスが戻らないため

| メソッド | パス | 結果 |
| --- | --- | --- |
| GET | `/api/sandbox` | 全件（image 無し） |
| GET | `/api/sandbox/{id}` | 1 件（image 有り）／無ければ 404 |
| POST | `/api/sandbox` | 201 ＋ Location |
| PUT | `/api/sandbox/{id}` | 部分更新／無ければ 404 |
| DELETE | `/api/sandbox/{id}` | 204／無ければ 404 |

> **Service 層は置いていない。**1 テーブルの単純な CRUD で、複数の更新を
> まとめる場面が無いため。**更新を 2 つ以上まとめる処理が出たら Service を作り、
> `@Transactional` をそこに付ける。**

---

## つまずいたときの早見表

| 症状 | 原因 | 対処 |
| --- | --- | --- |
| Eclipse が「開いていません」で起動しない | 公証されていない（Pleiades は自己署名） | `sudo xattr -dr com.apple.quarantine <app>` |
| ターミナルで `java: Unable to locate` | JDK が Eclipse 内にしかない | `JAVA_HOME` を明示する |
| `Non-resolvable parent POM` | Initializr が `.RELEASE` 付きで生成 | version から `.RELEASE` を削る |
| オフラインで `surefire-junit-platform` が無い | `go-offline` では取り切れない | オンラインで `./mvnw test` を通す |
| psql は繋がるがアプリは `Connection refused` | psql が UNIX ソケット経由だった | `psql -h localhost` で TCP を確認 |
| 急に DB に繋がらない | サービスが停止している | `brew services list` → `restart` |
| `/` が 404 | コントローラ未作成 | 正常。`/actuator/health` で確認する |
| `psql: command not found` | keg-only で PATH 未設定 | `~/.zshrc` に追記 → `rehash` |
| pgAdmin が `'Server Name' cannot be empty.` | 接続失敗ではなく表示名が未入力 | 任意の名前を入れる |
| `Invalid bound statement (not found)` | XML の namespace / id がインタフェースとずれている | 完全修飾名とメソッド名を突き合わせる |
| `code` の値に空白が付いてくる | `char(4)` は固定長で右詰めされる | `trim()` するか varchar に変える |
| INSERT が `null value in column "id"` | id に採番の仕組みが無い | sequence を付けて `useGeneratedKeys` にする |
| id が歯抜けになる | シーケンスはロールバックされない | 仕様。連番を保証する用途に PK を使わない |

---

## 未着手

- 入力検証（`@Valid` / Bean Validation は未導入）
- 例外ハンドリング（`@RestControllerAdvice` でエラー応答を統一する）
- `.gitignore` に Eclipse メタデータ（`.project` 等）を入れるかの判断

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
