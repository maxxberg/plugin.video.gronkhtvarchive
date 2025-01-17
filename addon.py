import sys
import requests
import xbmcgui
import xbmcplugin

python_version = sys.version_info[0]
try:
    from urllib import urlencode
    from urlparse import parse_qsl
except:
    from urllib.parse import urlencode, parse_qsl

API = "https://api.gronkh.tv/v1"
SEARCH_API = "https://api.gronkh.tv/v1/search"
PLAYLIST_API = "https://api.gronkh.tv/v1/video/playlist"

__url__ = sys.argv[0]
__handle__ = int(sys.argv[1])


# Getter functions
def get_all_streams(tags = None, search_string = None):
    all_vids = {}
    counter = 0
    params = {}
    if tags:
        params['tags']=','.join(tags)
    if search_string:
        params['query']=search_string
    while True:
        params.update({"offset": counter * 25, "first": 25})
        r = requests.get(SEARCH_API, params=params)
        try:
            vids = r.json()["results"]["videos"]
            for vid in vids:
                tags = [tag["title"] for tag in vid["tags"]]
                yield (vid["episode"], {"title": vid["title"],
                                            "length": vid["video_length"],
                                            "created_at": vid["created_at"][:10],
                                            "thumbnail": vid["preview_url"],
                                            "tags": tags
                                            })
            counter += 1
            if len(vids)==0:
                break
        except KeyError:
            break
    return all_vids

def get_all_tags():
    tags = {}
    r = requests.get(API + '/tags/all')
    if r.status_code == 200:
        return { item['id']:item['title'] for item in r.json() }


def get_stream_title(stream_dict, episode):
    return stream_dict[episode]["title"].split(" - ", 1)[1]


def get_keyboard_input():
    key_input = None
    keyboard = xbmc.Keyboard()
    keyboard.doModal()
    if keyboard.isConfirmed():
        if python_version == 2:
            key_input = unicode(keyboard.getText()).lower()
        else:
            key_input = keyboard.getText().lower()
    return key_input


def get_vid_links(episode):
    vid_links = {}
    r = requests.get(PLAYLIST_API, params={"episode": episode})
    playlist_url = r.json()["playlist_url"]

    data = requests.get(playlist_url).text
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


def get_created_month(created_at):
    return created_at[5:7]


def get_created_year(created_at):
    return created_at[:4]


def get_month_from_id(month_id):
    if month_id == -1:
        return -1
    month = month_id + 1
    month = "0" + str(month) if month < 10 else str(month)
    return month


# Search categories
def search_for_title():
    xbmcplugin.setPluginCategory(__handle__, "Titelsuche")
    xbmcplugin.setContent(__handle__, 'videos')
    key_input = get_keyboard_input()
    if key_input:
        all_streams = { episode:info for (episode,info) in get_all_streams(search_string=key_input) }
        create_streamlist(all_streams, sorted(all_streams, reverse=True))


def search_for_month():
    xbmcplugin.setPluginCategory(__handle__, "Monatssuche")
    xbmcplugin.setContent(__handle__, 'videos')
    months = ["Januar", "Februar", "Maerz", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
              "November", "Dezember"]
    month = get_month_from_id(xbmcgui.Dialog().select("Monat auswaehlen", months))
    if month != -1:
        all_streams_gen = get_all_streams()
        all_streams = {}
        found_streams = []
        for (episode, info) in all_streams_gen:
             if month == get_created_month(info["created_at"]):
                found_streams.append(episode)
                all_streams[episode] = info
                break
        for (episode, info) in all_streams_gen:
            if month == get_created_month(info["created_at"]):
                found_streams.append(episode)
                all_streams[episode] = info
            else:
                break
        create_streamlist(all_streams, sorted(found_streams, reverse=True))


def search_for_category_list():
    xbmcplugin.setPluginCategory(__handle__, "Kategoriesuche (Liste)")
    xbmcplugin.setContent(__handle__, 'videos')
    all_streams_gen = get_all_streams()
    all_streams = {}
    categories = get_all_tags()
    category = xbmcgui.Dialog().select("Kategorie auswaehlen", list(categories.values()))
    if category != -1:
        category = list(categories.keys())[category]
        found_streams = []
        for (episode, info) in get_all_streams(tags=[str(category)]):
            all_streams[episode] = info
        create_streamlist(all_streams, sorted(all_streams, reverse=True))


def search_for_category_freetext():
    xbmcplugin.setPluginCategory(__handle__, "Kategoriesuche (Freitext)")
    xbmcplugin.setContent(__handle__, 'videos')
    key_input = get_keyboard_input()
    if key_input:
        all_categories = get_all_tags()
        categories = [str(tag) for tag in all_categories if key_input in all_categories[tag].lower()]
        all_streams = { episode:info for (episode, info) in get_all_streams(categories) }
        create_streamlist(all_streams, sorted(all_streams, reverse=True))


def search_for_year():
    xbmcplugin.setPluginCategory(__handle__, "Jahressuche")
    xbmcplugin.setContent(__handle__, 'videos')
    key_input = get_keyboard_input()
    if key_input:
        if key_input.isdecimal():
            all_streams_gen = get_all_streams()
            all_streams = {}
            found_streams = []
            for (episode, info) in all_streams_gen:
                if key_input == get_created_year(info["created_at"]):
                    found_streams.append(episode)
                    all_streams[episode] = info
            create_streamlist(all_streams, sorted(found_streams, reverse=True))


def search_for_month_year():
    xbmcplugin.setPluginCategory(__handle__, "Monats- & Jahressuche")
    xbmcplugin.setContent(__handle__, 'videos')

    monate = ["Januar", "Februar", "Maerz", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
              "November", "Dezember"]
    month = get_month_from_id(xbmcgui.Dialog().select("Monat auswaehlen", monate))
    if month != -1:
        key_input = get_keyboard_input()
        if key_input:
            if key_input.isdecimal() and month != -1:
                all_streams_gen = get_all_streams()
                all_streams = {}
                found_streams = []
                for (episode, info) in all_streams_gen:
                    if key_input == get_created_year(info["created_at"]) and month == get_created_month(info["created_at"]):
                        found_streams.append(episode)
                        all_streams[episode] = info
                create_streamlist(all_streams, sorted(found_streams, reverse=True))


# Build UI
def search_menu():
    xbmcplugin.setPluginCategory(__handle__, 'Suche')
    xbmcplugin.setContent(__handle__, 'videos')
    items = ["Titel", "Monat", "Jahr", "Monat + Jahr", "Kategorie (Liste)", "Kategorie (Freitext)"]
    for item in items:
        list_item = xbmcgui.ListItem(label=item)
        url = get_url(action='listing', category=item)
        is_folder = True
        xbmcplugin.addDirectoryItem(__handle__, url, list_item, is_folder)
    xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(__handle__)


def all_streams_menu():
    xbmcplugin.setPluginCategory(__handle__, "Vergangene Streams")
    xbmcplugin.setContent(__handle__, 'videos')
    all_streams_gen = get_all_streams()
    all_streams = { episode:info for (episode, info) in all_streams_gen }
    sorted_episodes = sorted(all_streams.keys(), reverse=True)
    create_streamlist(all_streams, sorted_episodes)


def main_menu():
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


# Helper functions
def create_streamlist(all_streams_dict, streams_order):
    stream_list = []
    for episode in streams_order:
        title = get_stream_title(all_streams_dict, episode)
        list_item = xbmcgui.ListItem(label=title)
        list_item.setInfo('video', {'title': 'Stream ' + str(episode) + ": " + title,
                                    'episode': episode,
                                    'year': int(all_streams_dict[episode]["created_at"][:4]),
                                    'duration': int(all_streams_dict[episode]["length"]),
                                    'genre': 'Games',
                                    'mediatype': 'Video'})
        list_item.setArt(
            {'thumb': all_streams_dict[episode]['thumbnail'],
             'icon': all_streams_dict[episode]['thumbnail'],
             'fanart': all_streams_dict[episode]['thumbnail']})
        list_item.setProperty('IsPlayable', 'true')
        url = get_url(action='play', video=episode)
        is_folder = False
        stream_list.append((url, list_item, is_folder))
    xbmcplugin.addDirectoryItems(__handle__, stream_list)
    xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(__handle__)


def play_video(episode):
    path = get_vid_links(episode)
    sort_key = {"Adaptive": 0, "1080p60": 1, "720p": 2, "360p": 3}

    chosen_quality = xbmcgui.Dialog().select("Qualitaet auswaehlen", sorted(path.keys(), key=lambda i: sort_key[i]))
    if chosen_quality != -1:
        play_item = xbmcgui.ListItem(path=path[list(path.keys())[chosen_quality]])
        xbmcplugin.setResolvedUrl(__handle__, True, listitem=play_item)


def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params['action'] == 'listing':
            if params["category"] == "Vergangene Streams":
                all_streams_menu()
            elif params["category"] == "Streamsuche":
                search_menu()
            elif params["category"] == "Titel":
                search_for_title()
            elif params["category"] == "Monat":
                search_for_month()
            elif params["category"] == "Jahr":
                search_for_year()
            elif params["category"] == "Monat + Jahr":
                search_for_month_year()
            elif params["category"] == "Kategorie (Liste)":
                search_for_category_list()
            elif params["category"] == "Kategorie (Freitext)":
                search_for_category_freetext()
        elif params['action'] == 'play':
            play_video(params['video'])
        else:
            raise ValueError('Invalid paramstring: {}!'.format(paramstring))
    else:
        main_menu()


if __name__ == "__main__":
    router(sys.argv[2][1:])
