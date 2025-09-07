## Supabaseサーバーのセットアップ

1.  **Supabaseプロジェクトを作成**:
    * Supabaseのウェブサイトで新しいプロジェクトを作成します。
    * 「Database」セクションで、新しいテーブルを作成します。テーブル名は`messages`とし、以下の列（columns）を追加してください：
        * `id`: `uuid`型、主キー
        * `created_at`: `timestamp with time zone`型、デフォルトは`now()`
        * `number`: `int8`型
        * `name`: `text`型
        * `message`: `text`型
        * `seed`: `text`型
        * `channel`: `text`型
    * `Row Level Security` (RLS) を無効にしてください。

2.  **APIキーを取得**:
    * Supabaseの「API」設定ページに移動します。
    * `Project URL`と`anon public key`をコピーします。

3.  **.env.localファイルを編集**:
    * 生成された`.env.local`ファイルを開き、コピーしたURLとキーを以下のように貼り付けます：
        ```
        SUPABASE_URL="あなたのプロジェクトURL"
        SUPABASE_KEY="あなたのAPIキー"
        ```

4.  **サーバーを起動**:
    * Node.jsがインストールされていることを確認します。
    * ターミナルで以下のコマンドを実行します：
        ```bash
        npm install express @supabase/supabase-js body-parser dotenv cors
        node server.js
        ```

5.  **`bbs.html`を編集**:
    * JavaScriptコードのAPIエンドポイントを新しいサーバーに合わせて変更する必要があります。
        * `fetch('/bbs/api?...')` を `fetch('http://localhost:3000/get?...')` に変更。
        * `fetch('/bbs/result', ...)` を `fetch('http://localhost:3000/send', ...)` に変更。
        * `fetch('/bbs/how', ...)` を `fetch('http://localhost:3000/how', ...)` に変更。

これで、ローカルで`bbs.html`と連携する掲示板サーバーが起動します。
