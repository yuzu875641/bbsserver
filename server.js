// Node.jsとExpress.jsを使ったSupabaseサーバーのサンプル
// オリジナルのbbs.htmlと連携するように設計されています。

const express = require('express');
const { createClient } = require('@supabase/supabase-js');
const bodyParser = require('body-parser');
const dotenv = require('dotenv');
const cors = require('cors');

dotenv.config({ path: '.env.local' });

const app = express();
const port = process.env.PORT || 3000;

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

app.use(cors());
app.use(bodyParser.json());
app.use(express.static('public')); // 必要に応じて静的ファイルを提供

let messageCounter = 0; // メッセージの通し番号

// メッセージ送信エンドポイント
app.post('/send', async (req, res) => {
    const { name, message, seed, channel } = req.body;

    if (!message) {
        return res.status(400).send('メッセージが空です。');
    }

    try {
        messageCounter++;
        const { data, error } = await supabase
            .from('messages')
            .insert([
                {
                    number: messageCounter,
                    name: name || '名無し',
                    message: message,
                    seed: seed,
                    channel: channel
                }
            ]);

        if (error) throw error;
        res.status(200).send('メッセージが送信されました。');
    } catch (error) {
        console.error('メッセージの送信エラー:', error);
        res.status(500).send('メッセージの送信に失敗しました。');
    }
});

// メッセージ取得エンドポイント (bbs.htmlの/bbs/apiに対応)
app.get('/get', async (req, res) => {
    const { channel } = req.query;

    try {
        const { data, error } = await supabase
            .from('messages')
            .select('*')
            .eq('channel', channel || 'main')
            .order('number', { ascending: true });

        if (error) throw error;

        // bbs.htmlが期待するHTML形式に変換
        let htmlContent = '<h3>話題: 雑談</h3><br/><table>';
        data.forEach(msg => {
            htmlContent += `<tr><td>${msg.number}</td><td>${msg.name}</td><td>${msg.message}</td></tr>`;
        });
        htmlContent += '</table>';

        res.status(200).send(htmlContent);
    } catch (error) {
        console.error('メッセージの取得エラー:', error);
        res.status(500).send('メッセージの取得に失敗しました。');
    }
});

// メッセージ削除エンドポイント
app.get('/delete', async (req, res) => {
    const { number } = req.query;

    if (!number) {
        return res.status(400).send('削除するメッセージ番号を指定してください。');
    }

    try {
        const { data, error } = await supabase
            .from('messages')
            .update({ message: '削除されました', name: '削除されました' })
            .eq('number', number);

        if (error) throw error;
        res.status(200).send('メッセージが削除されました。');
    } catch (error) {
        console.error('メッセージの削除エラー:', error);
        res.status(500).send('メッセージの削除に失敗しました。');
    }
});

// /bbs/howエンドポイント
app.get('/how', (req, res) => {
    const commands = `
/delete [メッセージ番号]: メッセージを削除します。
/color [色コード]: 自分の名前の色を変更します。
`;
    res.status(200).send(commands);
});

app.listen(port, () => {
    console.log(`Server is running at http://localhost:${port}`);
});
