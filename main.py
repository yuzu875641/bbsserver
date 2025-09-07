# ファイル名: main.py
import json
import requests
import urllib.parse
import time
import os
import re
import base64
from typing import Union

from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi import Response, Cookie, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.responses import RedirectResponse as redirect
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.templating import Jinja2Templates

from cachetools import TTLCache, cached
from dotenv import load_dotenv

load_dotenv()

# `cachetools` ライブラリを使用してキャッシュを実装
cache_bbs_api = TTLCache(maxsize=100, ttl=5)
cache_how = TTLCache(maxsize=100, ttl=30)

# 環境変数からURLを取得
YUKI_BBS_URL = os.getenv("YUKI_BBS_URL")
if not YUKI_BBS_URL:
    raise ValueError("環境変数 'YUKI_BBS_URL' が設定されていません。")

version = "1.0"


def get_info(request):
    """
    リクエスト情報をJSON形式で返すヘルパー関数
    """
    global version
    return json.dumps(
        [
            version,
            os.environ.get("RENDER_EXTERNAL_URL"),
            str(request.scope["headers"]),
        ]
    )


def parse_html_to_json(html_content):
    """
    HTMLコンテンツを解析してJSON形式に変換する関数
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # 話題を取得
    topic = ""
    if soup.find('h3'):
        topic_html = str(soup.find('h3').decode_contents())
        topic = topic_html.replace('<br>', '\n').replace('<br/>', '\n')[5:]

    messages = []
    for row in soup.find_all('tr')[1:]:  # ヘッダー行をスキップ
        cols = row.find_all('td')
        if len(cols) == 3:
            number = cols[0].get_text()
            name_cell = cols[1]

            # 名前の色を取得
            name_color = None
            name_font = name_cell.find('font', color=True)
            if name_font and not name_font.get_text().startswith('@'):
                name_color = name_font.get('color')

            # IDとその色を取得
            id_match = re.search(r'@[A-Za-z0-9]{7}', name_cell.get_text())
            user_id = id_match.group(0) if id_match else None
            id_color = None
            id_font = name_cell.find('font', string=lambda s: s and '@' in s)
            if id_font:
                id_color = id_font.get('color')

            # 追加テキストを取得
            extra_text = None
            extra_font_list = name_cell.find_all('font')
            if extra_font_list:
                extra_font = extra_font_list[-1]
                if extra_font.get('color', '') == 'magenta':
                    extra_text = extra_font.get_text()

            # 名前を取得（色付きフォントとIDを除いた部分）
            name = name_cell.get_text()
            if user_id:
                name = name.replace(user_id, '').strip()
            if extra_text:
                name = name.replace(extra_text, '').strip()

            messages.append({
                'number': number,
                'name': name,
                'name_color': name_color,
                'user_id': user_id,
                'id_color': id_color,
                'extra_text': extra_text,
                'message': cols[2].get_text().replace('<br>', '\n').replace('<br/>', '\n')
            })

    return {
        'topic': topic,
        'messages': messages
    }


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(GZipMiddleware, minimum_size=1000)

base_dir = os.path.dirname(os.path.abspath(__file__))
template = Jinja2Templates(directory=os.path.join(base_dir, "views")).TemplateResponse


@app.get("/", response_class=HTMLResponse)
def home(response: Response, request: Request, yuki: Union[str] = Cookie(None)):
    return redirect("/bbs")


@app.get("/bbs", response_class=HTMLResponse)
def view_index(
    request: Request,
    name: Union[str, None] = "",
    seed: Union[str, None] = "",
    channel: Union[str, None] = "main",
    verify: Union[str, None] = "false",
    yuki: Union[str] = Cookie(None),
):
    return template("bbs.html", {"request": request})


@app.get("/bbs/info", response_class=HTMLResponse)
def view_info(
    request: Request,
    name: Union[str, None] = "",
    seed: Union[str, None] = "",
    channel: Union[str, None] = "main",
    verify: Union[str, None] = "false",
    yuki: Union[str] = Cookie(None),
):
    res = HTMLResponse(requests.get(f"{YUKI_BBS_URL}/bbs/info").text)
    return res


@cached(cache_bbs_api)
def bbsapi_cached(verify, channel):
    """
    BBS APIへのリクエストをキャッシュする関数
    """
    return requests.get(
        f"{YUKI_BBS_URL}/bbs/api?t={urllib.parse.quote(str(int(time.time() * 1000)))}&verify={urllib.parse.quote(verify)}&channel={urllib.parse.quote(channel)}",
        cookies={"yuki": "True"},
    ).text


@app.get("/bbs/api", response_class=HTMLResponse)
def view_bbs(
    request: Request,
    t: str,
    channel: Union[str, None] = "main",
    verify: Union[str, None] = "false",
):
    html_content = bbsapi_cached(verify, channel)
    json_data = parse_html_to_json(html_content)
    return json.dumps(json_data, ensure_ascii=False)


@app.post("/bbs/result")
async def write_bbs(request: Request):
    """
    メッセージを投稿するエンドポイント
    """
    body = await request.json()
    message = base64.b64decode(body['message']).decode("utf-8")
    message = message.replace('\n', '<br>')
    name = body.get('name', '')
    seed = body.get('seed', '')
    channel = body.get('channel', 'main')
    verify = body.get('verify', 'false')

    try:
        t = requests.post(
            f"{YUKI_BBS_URL}/bbs/result?name={urllib.parse.quote(name)}&message={urllib.parse.quote(message)}&seed={urllib.parse.quote(seed)}&channel={urllib.parse.quote(channel)}&verify={urllib.parse.quote(verify)}&info={urllib.parse.quote(get_info(request))}",
            cookies={"yuki": "True"},
            allow_redirects=False,
            timeout=10
        )
        return HTMLResponse(t.text)
    except requests.exceptions.Timeout:
        return HTMLResponse("サーバーからの応答がありません。時間切れです。", status_code=504)
    except requests.exceptions.RequestException as e:
        return HTMLResponse(f"リクエスト中にエラーが発生しました: {e}", status_code=500)


@cached(cache_how)
def how_cached():
    """
    how APIへのリクエストをキャッシュする関数
    """
    try:
        return requests.get(f"{YUKI_BBS_URL}/bbs/how").text
    except requests.exceptions.RequestException:
        return "ヘルプテキストの取得に失敗しました。"


@app.get("/bbs/how", response_class=PlainTextResponse)
def view_commonds(request: Request, yuki: Union[str] = Cookie(None)):
    return how_cached()


@app.get("/load_instance")
def reload():
    """
    インスタンスURLを再読み込みするエンドポイント
    """
    try:
        global YUKI_BBS_URL
        YUKI_BBS_URL = requests.get(
            r"https://raw.githubusercontent.com/mochidukiyukimi/yuki-youtube-instance/main/instance.txt"
        ).text.rstrip()
        return {"status": "ok", "new_url": YUKI_BBS_URL}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"URLの取得に失敗しました: {e}"}
