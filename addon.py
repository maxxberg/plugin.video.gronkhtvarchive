import sys
import requests
from urllib import urlencode
from urlparse import parse_qsl
import urllib3
import xbmcgui
import xbmcplugin


SEARCH_API = "https://api.gronkh.tv/v1/search"
PLAYLIST_API = "https://api.gronkh.tv/v1/video/playlist"

__url__ = sys.argv[0]
__handle__ = int(sys.argv[1])


def get_all_streams():
    all_vids = {}
    counter = 0
    while True:
        r = requests.get(SEARCH_API, params={"offset": counter * 25, "first": 25})
        try:
            vids = r.json()["results"]["videos"]
            for vid in vids:
                all_vids[vid["episode"]] = {"title": vid["title"], "length": vid["video_length"],
                                            "created_at": vid["created_at"][:10], "thumbnail": vid["preview_url"]}
            counter += 1
        except KeyError:
            break
    return all_vids


def get_stream_title(stream_dict, episode):
    return stream_dict[episode]["title"].split(" - ", 1)[1]


def get_vid_links(episode):
    vid_links = {}
    r = requests.get(PLAYLIST_API, params={"episode": episode})
    playlist_url = r.json()["playlist_url"]

    http = urllib3.PoolManager()
    data = http.request("GET", playlist_url).data.decode("utf-8")
    current_resolution = ""
    for line in data.split("\n"):
        if line.startswith("#EXT-X-STREAM-INF:") or line.startswith("https"):
            if line.startswith("#EXT-X-STREAM-INF:"):
                current_resolution = line.split(":")[1].split(",")[-1].split("=")[1].replace('"', "").strip()
                continue
            else:
                vid_links[current_resolution] = line.strip()
    vid_links["Adaptive"] = playlist_url

    return vid_links


def get_url(**kwargs):
    return '{}?{}'.format(__url__, urlencode(kwargs))


def play_video(episode):
    path = get_vid_links(episode)
    sort_key = {"Adaptive": 0, "1080p60": 1, "720p": 2, "360p": 3}

    chosen_quality = xbmcgui.Dialog().select("Qualitaet auswaehlen", sorted(path.keys(), key=lambda i: sort_key[i]))
    if chosen_quality != -1:
        play_item = xbmcgui.ListItem(path=path[path.keys()[chosen_quality]])
        xbmcplugin.setResolvedUrl(__handle__, True, listitem=play_item)


def search_title():
    xbmcplugin.setPluginCategory(__handle__, "Titelsuche")
    xbmcplugin.setContent(__handle__, 'videos')
    keyboard = xbmc.Keyboard()
    keyboard.doModal()
    if (keyboard.isConfirmed()):
        input = keyboard.getText()
        input = input.lower()
        all_streams = get_all_streams()
        found_streams = []
        for episode, info in all_streams.items():
            if input in info["title"].lower():
                found_streams.append(episode)
        create_streamlist(all_streams, sorted(found_streams, reverse=True))


def get_created_month(created_at):
    return created_at[5:7]


def get_created_year(created_at):
    return created_at[:4]


def get_month_from_id(month_id):
    if month_id == -1:
        return
    month = month_id + 1
    month = "0" + str(month) if month < 10 else str(month)
    return month


def search_month():
    xbmcplugin.setPluginCategory(__handle__, "Monatssuche")
    xbmcplugin.setContent(__handle__, 'videos')
    monate = ["Januar", "Februar", "Maerz", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
              "November", "Dezember"]
    month = get_month_from_id(xbmcgui.Dialog().select("Monat auswaehlen", monate))
    if month != -1:
        all_streams = get_all_streams()
        found_streams = []
        for episode, info in all_streams.items():
            if month == get_created_month(info["created_at"]):
                found_streams.append(episode)
        create_streamlist(all_streams, sorted(found_streams, reverse=True))


def search_year():
    xbmcplugin.setPluginCategory(__handle__, "Jahrsuche")
    xbmcplugin.setContent(__handle__, 'videos')

    keyboard = xbmc.Keyboard()
    keyboard.doModal()
    if (keyboard.isConfirmed()):
        input = unicode(keyboard.getText())
        if input.isdecimal():
            all_streams = get_all_streams()
            found_streams = []
            for episode, info in all_streams.items():
                if input == get_created_year(info["created_at"]):
                    found_streams.append(episode)
            create_streamlist(all_streams, sorted(found_streams, reverse=True))


def search_month_year():
    xbmcplugin.setPluginCategory(__handle__, "Jahrsuche")
    xbmcplugin.setContent(__handle__, 'videos')

    monate = ["Januar", "Februar", "Maerz", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
              "November", "Dezember"]
    month = get_month_from_id(xbmcgui.Dialog().select("Monat auswaehlen", monate))
    keyboard = xbmc.Keyboard()
    keyboard.doModal()
    if (keyboard.isConfirmed()):
        input = unicode(keyboard.getText())
        if input.isdecimal() and month != -1:
            all_streams = get_all_streams()
            found_streams = []
            for episode, info in all_streams.items():
                if input == get_created_year(info["created_at"]) and month == get_created_month(info["created_at"]):
                    found_streams.append(episode)
            create_streamlist(all_streams, sorted(found_streams, reverse=True))


def create_streamlist(all_streams_dict, streams_order):
    for episode in streams_order:
        title = get_stream_title(all_streams_dict, episode)
        list_item = xbmcgui.ListItem(label=title)
        list_item.setInfo('video', {'title': 'Stream ' + str(episode) + ": " + title,
                                    'episode': episode,
                                    'year': int(all_streams_dict[episode]["created_at"][:4]),
                                    'duration': int(all_streams_dict[episode]["length"]),
                                    'genre': 'Games',
                                    'mediatype': 'Stream'})
        list_item.setArt({'thumb': all_streams_dict[episode]['thumbnail'], 'icon': all_streams_dict[episode]['thumbnail'],
                          'fanart': all_streams_dict[episode]['thumbnail']})
        list_item.setProperty('IsPlayable', 'true')
        url = get_url(action='play', video=episode)
        is_folder = False
        xbmcplugin.addDirectoryItem(__handle__, url, list_item, is_folder)
    xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(__handle__)


def list_all_streams():
    xbmcplugin.setPluginCategory(__handle__, "Vergangene Streams")
    xbmcplugin.setContent(__handle__, 'videos')
    all_streams = get_all_streams()
    sorted_episodes = sorted(all_streams.keys(), reverse=True)
    create_streamlist(all_streams, sorted_episodes)


def list_categories():
    xbmcplugin.setPluginCategory(__handle__, '')
    xbmcplugin.setContent(__handle__, 'videos')
    items = ["Vergangene Streams", "Streamsuche"]
    for item in items:
        list_item = xbmcgui.ListItem(label=item)
        url = get_url(action='listing', category=item)
        is_folder = True
        xbmcplugin.addDirectoryItem(__handle__, url, list_item, is_folder)
    xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(__handle__)


def list_search():
    xbmcplugin.setPluginCategory(__handle__, 'Streamsuche')
    xbmcplugin.setContent(__handle__, 'videos')
    items = ["Titel", "Monat", "Jahr", "Monat + Jahr"]
    for item in items:
        list_item = xbmcgui.ListItem(label=item)
        url = get_url(action='listing', category=item)
        is_folder = True
        xbmcplugin.addDirectoryItem(__handle__, url, list_item, is_folder)
    xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(__handle__)


def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params['action'] == 'listing':
            if params["category"] == "Vergangene Streams":
                list_all_streams()
            elif params["category"] == "Streamsuche":
                list_search()
            elif params["category"] == "Titel":
                search_title()
            elif params["category"] == "Monat":
                search_month()
            elif params["category"] == "Jahr":
                search_year()
            elif params["category"] == "Monat + Jahr":
                search_month_year()
        elif params['action'] == 'play':
            play_video(params['video'])
        else:
            raise ValueError('Invalid paramstring: {}!'.format(paramstring))
    else:
        list_categories()


if __name__ == "__main__":
    router(sys.argv[2][1:])