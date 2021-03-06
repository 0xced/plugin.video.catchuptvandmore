# -*- coding: utf-8 -*-
"""
    Catch-up TV & More
    Copyright (C) 2017  SylvainCecchetto

    This file is part of Catch-up TV & More.

    Catch-up TV & More is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    Catch-up TV & More is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with Catch-up TV & More; if not, write to the Free Software Foundation,
    Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

# The unicode_literals import only has
# an effect on Python 2.
# It makes string literals as unicode like in Python 3
from __future__ import unicode_literals

from codequick import Route, Resolver, Listitem, utils, Script


from resources.lib import web_utils
from resources.lib import download
from resources.lib.menu_utils import item_post_treatment

import json
import re
import urlquick

URL_ROOT = 'http://www.nhk.or.jp'

URL_NHK_LIFESTYLE = URL_ROOT + '/lifestyle/'

URL_API_KEY_NHK = 'http://movie-s.nhk.or.jp/player.php?v=%s&wmode=transparen&r=true'
# VideoId

URL_API_STREAM_NHK = 'http://movie-s.nhk.or.jp/ws/ws_program/api/%s/apiv/5/mode/json?v=%s'
# Api_Key, VideoId


def replay_entry(plugin, item_id, **kwargs):
    """
    First executed function after replay_bridge
    """
    return list_categories(plugin, item_id)


@Route.register
def list_categories(plugin, item_id, **kwargs):
    """
    Build categories listing
    - Tous les programmes
    - Séries
    - Informations
    - ...
    """
    resp = urlquick.get(URL_NHK_LIFESTYLE)
    root = resp.parse()

    for category_datas in root.iterfind(
            ".//h2[@class='p-sliderSection__heading']"):
        if category_datas.find('.//a') is not None:
            if category_datas.find('.//a').get('class') is not None:
                if 'text-color-' in category_datas.find('.//a').get('class'):
                    category_title = category_datas.find('.//a').text
                    category_url = URL_NHK_LIFESTYLE + category_datas.find(
                        './/a').get('href')

                    item = Listitem()
                    item.label = category_title
                    item.set_callback(list_videos,
                                      item_id=item_id,
                                      category_url=category_url)
                    item_post_treatment(item)
                    yield item


@Route.register
def list_videos(plugin, item_id, category_url, **kwargs):

    resp = urlquick.get(category_url)
    root = resp.parse()
    list_videos_datas_json_value = root.find('.//article').findall(
        './/script')[0].text

    # TODO try to simplify it
    list_videos_datas_json_value = list_videos_datas_json_value.replace(
        ']', '')
    list_videos_datas_json_value = list_videos_datas_json_value.replace(
        'var NHKLIFE_LISTDATA = [', '')
    list_videos_datas_json_value = list_videos_datas_json_value.strip()
    list_videos_datas_json_value = list_videos_datas_json_value.replace(
        '{', '{"')
    list_videos_datas_json_value = list_videos_datas_json_value.replace(
        ': ', '": ')
    list_videos_datas_json_value = list_videos_datas_json_value.replace(
        ',', ',"')
    list_videos_datas_json_value = list_videos_datas_json_value.replace(
        ',"{', ',{')
    json_parser = json.loads('[' + list_videos_datas_json_value + ']')

    for video_datas in json_parser:
        if 'video' in video_datas["href"]:
            video_title = video_datas["title"]
            video_plot = video_datas["desc"]
            if 'www.nhk.or.jp' in video_datas["image_src"]:
                video_image = 'http:' + video_datas["image_src"]
            else:
                video_image = URL_ROOT + video_datas["image_src"]
            video_duration = 60 * int(video_datas["videoInfo"]["duration"].split(':')[0]) + \
                int(video_datas["videoInfo"]["duration"].split(':')[1])
            video_url = URL_NHK_LIFESTYLE + video_datas["href"].replace(
                '../', '')

            item = Listitem()
            item.label = video_title
            item.art['thumb'] = item.art['landscape'] = video_image
            item.info['plot'] = video_plot
            item.info['duration'] = video_duration

            item.set_callback(get_video_url,
                              item_id=item_id,
                              video_url=video_url)
            item_post_treatment(item, is_playable=True, is_downloadable=True)
            yield item


@Resolver.register
def get_video_url(plugin,
                  item_id,
                  video_url,
                  download_mode=False,
                  **kwargs):

    resp = urlquick.get(video_url)
    if re.compile('player.php\?v=(.*?)&').findall(resp.text):
        video_id = re.compile('player.php\?v=(.*?)&').findall(resp.text)[0]
    else:
        video_id = re.compile('movie-s.nhk.or.jp/v/(.*?)\?').findall(
            resp.text)[0]
    resp2 = urlquick.get(URL_API_KEY_NHK % video_id)
    api_key_value = re.compile('data-de-api-key="(.*?)"').findall(
        resp2.text)[0]
    resp3 = urlquick.get(URL_API_STREAM_NHK % (api_key_value, video_id))
    json_parser = json.loads(resp3.text)
    final_video_url = json_parser["response"]["WsProgramResponse"]["program"][
        "asset"]["ipadM3u8Url"]
    if download_mode:
        return download.download_video(final_video_url)
    return final_video_url
