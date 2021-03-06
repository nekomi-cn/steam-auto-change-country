# coding: utf-8
from email.policy import default
import re
import traceback

from flask import Flask
from flask import request
from flask import make_response
import urllib.parse
import requests
from requests_html import HTMLSession
from bs4.element import Tag
from bs4 import BeautifulSoup
import urllib3

app = Flask(__name__)
app.url_map.strict_slashes = False

STEAM_URL = "https://store.steampowered.com"
DELIVERY_AREA = "HK"

GAME_URL = ""

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def proxy_pass_request(redirect_url, request_method, request_params):

    session = HTMLSession()
    response = session.request(
        request_method,
        redirect_url,
        verify=False,
        # stream=True,
        headers=request_params['headers']
    )

    return response

# 注入国家更改脚本


def generate_delivery_game_script(delivery_area, session_id, steam_country):
    notes = ""
    # print(steam_country)
    if DELIVERY_AREA in steam_country:
        notes = r"//"
    origin_js = """
jQuery.post('https://store.steampowered.com/account/setcountry/', {
    sessionid: '%s',
    cc: '%s'
}, function(result) {
    %s window.location.reload()
})
""" % (
            session_id,
            delivery_area,
            notes
        )
    
    return origin_js

# 获取 SessionID 和 AccountID


def get_steam_params_from_response(response_content):
    """
        var g_AccountID = 86433468;
        var g_sessionID = "32ef6dfb0621ece4f257501d";
        var g_ServerTime = 1624366269;
        GDynamicStore.Init( 86433468, false, "win", {"primary_language":6,"secondary_languages":128,"platform_windows":1,"platform_mac":0,"platform_linux":0,"hide_adult_content_violence":0,"hide_adult_content_sex":0,"timestamp_updated":1642679434,"hide_store_broadcast":0,"review_score_preference":0,"timestamp_content_descriptor_preferences_updated":1536395468,"provide_deck_feedback":0}, 'CN',
			{"bNoDefaultDescriptors":false} );
    """
    session_id_str = re.search(r'var g_sessionID = "(\w+?)";',
                               response_content)
    if not session_id_str:
        return False

    account_id_str = re.search(r'var g_AccountID = (\w+?);',
                               response_content)

    steam_country_str1 = re.search(r'provide_deck_feedback(.*)', response_content)
    steam_country_str = re.search(r", '(.*)", steam_country_str1)
    if not steam_country_str:
        return False
    if not account_id_str:
        return False

    session_id = session_id_str.groups()[0]
    account_id = account_id_str.groups()[0]
    steam_country = steam_country_str.group().replace(", '", "")
    steam_country = steam_country.replace("',", "")
    # print(steam_country)
    return {
        'session_id': session_id,
        'account_id': account_id,
        'steam_country': steam_country
    }

# 注入 Script 脚本


def insert_scripts_to_response_content(response_content, scripts):
    bs_obj = BeautifulSoup(response_content, features="lxml")
    script_tag = Tag(name='script')
    script_tag.string = scripts
    bs_obj.head.append(script_tag)
    return str(bs_obj)


def data_deal(request_params):
    proxy_result = proxy_pass_request(GAME_URL, 'GET', request_params)
    ignore_headers = ['Server', 'Content-Type',
                      'Content-Encoding', 'Connection', 'Vary', 'Content-Length']
    try:
        if proxy_result.status_code == 200:
            steam_params = get_steam_params_from_response(
                proxy_result.html.html)
            # print(steam_params)
            if steam_params:
                delivery_scripts = generate_delivery_game_script(DELIVERY_AREA, steam_params['session_id'], steam_params['steam_country'])
                new_response = insert_scripts_to_response_content(proxy_result.html.html,
                                                                delivery_scripts)

                resp = make_response(new_response)
                for item_key in proxy_result.headers:
                    if item_key not in ignore_headers:
                        resp.headers[item_key] = proxy_result.headers[item_key]
                return resp, proxy_result.status_code
    except Exception as e:
        print(traceback.format_exc())
    resp = make_response(proxy_result.html.html)
    for item_key in proxy_result.headers:
        if item_key not in ignore_headers:
            resp.headers[item_key] = proxy_result.headers[item_key]
    return resp, proxy_result.status_code


def generate_format_cookies(origin_cookie_str):
    cookies = {}
    for item_cookie_pair in origin_cookie_str.split(';'):
        if item_cookie_pair:
            cookie_key, cookie_value = item_cookie_pair.split('=')
            cookies[cookie_key.lstrip()] = urllib.parse.unquote(cookie_value)
    return cookies


@app.route('/app/<gameid>', defaults={'gamename': None})
@app.route('/app/<gameid>/<gamename>')
def steam_data_proxy_pass(gameid, gamename):
    global GAME_URL
    if gamename:
        GAME_URL = STEAM_URL + f"/app/{gameid}/{gamename}/"
    else:
        GAME_URL = STEAM_URL + f"/app/{gameid}/"
    request_headers = dict(request.headers or {})
    request_params = dict(request.args or {})
    request_post_data = dict(request.form or {})
    request_json = dict(request.json or {})
    request_headers.pop('X-Real-Ip', '')
    request_headers.pop('X-Forwarded-For', '')
    request_headers.pop('Accept-Encoding', '')
    request_headers['Connection'] = 'keep-alive'
    request_cookies = request_headers.get('Cookie', '')
    formated_cookies = generate_format_cookies(request_cookies)
    headers = {}
    request_headers.get('Cookie') and headers.update(
        {'Cookie': request_headers.get('Cookie')})
    request_headers.get(
        'User-Agent') and headers.update({'User-Agent': request_headers.get('User-Agent')})
    request_headers.get('Accept') and headers.update(
        {'Accept': request_headers.get('Accept')})
    request_headers.get('Accept-Language') and headers.update(
        {'Accept-Language': request_headers.get('Accept-Language')})
    request_headers.get(
        'sec-ch-ua') and headers.update({'sec-ch-ua': request_headers.get('sec-ch-ua')})
    request_headers.get('sec-ch-ua-mobile') and headers.update(
        {'sec-ch-ua-mobile': request_headers.get('sec-ch-ua-mobile')})
    request_headers.get('Sec-Fetch-Dest') and headers.update(
        {'Sec-Fetch-Dest': request_headers.get('Sec-Fetch-Dest')})
    request_headers.get('Sec-Fetch-Mode') and headers.update(
        {'Sec-Fetch-Mode': request_headers.get('Sec-Fetch-Mode')})
    request_headers.get(
        'Sec-Fetch-User') and headers.update({'Sec-Fetch-User': 1})
    request_headers.get('Upgrade-Insecure-Requests') and headers.update(
        {'Upgrade-Insecure-Requests': request_headers.get('Upgrade-Insecure-Requests')})
    request_headers['Host'] = 'store.steampowered.com'

    request_params = {
        'data': request_post_data,
        'params': request_params,
        'json': request_json,
        'headers': request_headers,
        # 'cookies': formated_cookies
    }
    # print('receive params %s' % request_params)
    return data_deal(request_params)

def test_render():
    headers = {'Host': 'store.steampowered.com', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Cache-Control': 'no-cache', 'Sec-Ch-Ua': '"Chromium";v="86", "\\"Not\\\\A;Brand";v="99", "Google Chrome";v="86"', 'Sec-Ch-Ua-Mobile': '?0', 'Upgrade-Insecure-Requests': '1',
               'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.183 Safari/537.36', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Sec-Fetch-Site': 'none', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-User': '?1', 'Sec-Fetch-Dest': 'document', 'Accept-Language': 'zh-CN,zh;q=0.9'}
    session = HTMLSession()
    resp = session.get(GAME_URL, headers=headers, verify=False)
    return resp


if __name__ == '__main__':
    print('start server')
    # test_render()
    app.run(host='0.0.0.0', port=5555, debug=False)
