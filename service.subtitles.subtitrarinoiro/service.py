# -*- coding: utf-8 -*-

import os
import re
import shutil
import sys
import unicodedata
import urllib
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs


__addon__ = xbmcaddon.Addon()
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')

__cwd__        = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__    = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__resource__   = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')).decode("utf-8")
__temp__       = xbmc.translatePath(os.path.join(__profile__, 'temp', ''))

BASE_URL = "http://www.subtitrari-noi.ro/"

sys.path.append (__resource__)
import requests

def Search(item):
    search_data = []
    try:
        search_data = searchsubtitles(item)
    except:
        xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__, 'eroare la cautare')).encode('utf-8'))
        return
    if search_data != None:
        dialog = xbmcgui.Dialog()
        if len(search_data) > 1: sel = dialog.select("Select item", [item_data["SubFileName"] for item_data in search_data])
        else: sel = 0
        if sel >= 0:
            try:
                for root, dirs, fileg in os.walk(__temp__, topdown=False):
                    for name in fileg:
                        filename = os.path.join(root, name)
                        os.remove(filename)
                    for name in dirs: os.rmdir(os.path.join(root, name))
                os.rmdir(__temp__)
            except: xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__, 'Nu s-au putut sterge fisierele temporare')).encode('utf-8'))
            xbmcvfs.mkdirs(__temp__)
            exts = [".srt", ".sub", ".txt", ".smi", ".ssa", ".ass"]
            log(__name__, "Download Using HTTP")
            s = requests.Session()
            ua = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64; rv:16.0.1) Gecko/20121011 Firefox/16.0.1'
            headers = {'User-Agent': ua}
            link = search_data[sel]["ZipDownloadLink"]
            filed = s.get(link, headers=headers)
            Type = 'rar' if link[-4:] == '.rar"' else 'zip'
            fname = "%s.%s" % (os.path.join(__temp__, "subtitle"), Type)
            with open(fname, 'wb') as f: f.write(filed.content)
            extractPath = os.path.join(__temp__, "Extracted")
            xbmc.executebuiltin(("XBMC.Extract(%s, %s)" % (fname, extractPath)), True)
            all_files = []
            for root, dirs, files in os.walk(extractPath):
                for filex in files:
                    dirfile = os.path.join(root, filex)
                    if (os.path.splitext(filex)[1] in exts):
                        all_files.append(dirfile)
            all_files = sorted(all_files, key=natural_key)
            for ofile in all_files:
                dirfile_with_path_name = normalizeString(os.path.relpath(ofile, extractPath))
                dirname, basename = os.path.split(dirfile_with_path_name)
                listitem = xbmcgui.ListItem(label=search_data[sel]["Traducator"],
                                        label2=('%s/%s' % (os.path.split(os.path.dirname(ofile))[-1], basename)) if (basename.lower() == os.path.split(all_files[0].lower())[-1] and ((basename.lower() == os.path.split(all_files[1].lower())[-1]) if len(all_files) > 1 else ('' == '0'))) else basename,
                                        iconImage=search_data[sel]["SubRating"],
                                        thumbnailImage=search_data[sel]["ISO639"]
                                        )
                url = "plugin://%s/?action=setsub&link=%s&filename=%s" % (__scriptid__,
                                                                            urllib.quote_plus(ofile),
                                                                            search_data[sel]["SubFileName"]
                                                                            )
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)

def searchsubtitles(item):
    if len(item['tvshow']) > 0:
        search_string = item['tvshow'].replace(" ", "+")
    else:
        if str(item['year']) == "":
            item['title'], item['year'] = xbmc.getCleanMovieTitle(item['title'])
    
        search_string = (re.sub('S(\d{1,2})E(\d{1,2})', '', item['title'])).replace(" ", "+")

    if item['mansearch']:
        s_string = urllib.unquote(item['mansearchstr'])
        search_string = s_string.replace(" ", "+")
    s = requests.Session()
    ua = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64; rv:16.0.1) Gecko/20121011 Firefox/16.0.1'
    headers = {'User-Agent': ua, 'Host': 'subtitrari-noi.ro', 'Referer': 'http://subtitrari-noi.ro/', 'X-Requested-With': 'XMLHttpRequest'}
    search_link = 'http://subtitrari-noi.ro/paginare_filme.php?search_q=1&query_q=%s&cautare=%s&tip=2&an=Toti+anii' % (search_string, search_string)
    search_code = s.post(search_link, headers=headers)
    regex = '''-main".+?(?:<p(?:.+?|)>(.+?)</p>){1}(?:<p(?:\s*|)>(.+?)</p>){3}.+?href=['"](.+?)['"].+?bottom.+?<div>(.+?)</div'''
    match = []
    for nume, traducator, legatura, descriere in re.compile(regex, re.IGNORECASE | re.DOTALL).findall(search_code.text):
        legatura = BASE_URL + legatura
        traducator = re.sub('traducator:', '', traducator, flags=re.I)
        match.append((nume,
                traducator,
                legatura,
                descriere,
                ))
    clean_search = []
    if len(match) > 0:
        for item_search in match:
            s_title = re.sub('\s+', ' ', cleanhtml(item_search[0])) + ' ' + re.sub('\s+', ' ', cleanhtml(item_search[3])) + ' Traducator: ' + re.sub('\s+', ' ', cleanhtml(item_search[1]))
            clean_search.append({'SeriesSeason': '0', 'SeriesEpisode': '0', 'LanguageName': 'Romanian', 'episode': '0', 'SubFileName': s_title, 'SubRating': '5', 'ZipDownloadLink': item_search[2], 'ISO639': 'ro', 'SubFormat': 'srt', 'MatchedBy': 'fulltext', 'SubHearingImpaired': '0', 'Traducator': re.sub('\s+', ' ', cleanhtml(item_search[1])), 'referer': search_string})
        if clean_search:
            return clean_search 
    else:
        return None  

def safeFilename(filename):
    keepcharacters = (' ', '.', '_', '-')
    return "".join(c for c in filename if c.isalnum() or c in keepcharacters).rstrip()

def natcasesort(arr):
    if isinstance(arr, list):
        arr = sorted(arr, key=lambda x:str(x).lower())
    elif isinstance(arr, dict):
        arr = sorted(arr.iteritems(), key=lambda x:str(x[0]).lower())
    return arr

def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg,)).encode('utf-8'), level=xbmc.LOGDEBUG) 

def natural_key(string_):
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string_)]

def normalizeString(obj):
    try:
        return unicodedata.normalize(
                                     'NFKD', unicode(unicode(obj, 'utf-8'))
                                     ).encode('ascii', 'ignore')
    except:
        return unicode(str(obj).encode('string_escape'))

def get_params(string=""):
    param = []
    if string == "":
        paramstring = sys.argv[2]
    else:
        paramstring = string
    if len(paramstring) >= 2:
        params = paramstring
        cleanedparams = params.replace('?', '')
        if (params[len(params)-1] == '/'):
            params = params[0:len(params)-2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]

    return param

params = get_params()

if params['action'] == 'search' or params['action'] == 'manualsearch':
    log(__name__, "action '%s' called" % params['action'])
    item = {}
    item['temp']               = False
    item['rar']                = False
    item['mansearch']          = False
    item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                         # Year
    item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                  # Season
    item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                 # Episode
    item['tvshow']             = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))  # Show
    item['title']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))# try to get original title
    item['file_original_path'] = xbmc.Player().getPlayingFile().decode('utf-8')                 # Full path of a playing file
    item['3let_language']      = [] #['scc','eng']

    if 'searchstring' in params:
        item['mansearch'] = True
        item['mansearchstr'] = params['searchstring']

    if item['title'] == "":
        log(__name__, "VideoPlayer.OriginalTitle not found")
        item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))      # no original title, get just Title

    if item['episode'].lower().find("s") > -1:                                      # Check if season is "Special"
        item['season'] = "0"                                                          #
        item['episode'] = item['episode'][-1:]

    if (item['file_original_path'].find("http") > -1):
        item['temp'] = True

    elif (item['file_original_path'].find("rar://") > -1):
        item['rar']  = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif (item['file_original_path'].find("stack://") > -1):
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    Search(item)

elif params['action'] == 'setsub':
    try: xbmc.Player().setSubtitles(urllib.unquote_plus(params['link']))
    except: pass
    listitem = xbmcgui.ListItem(label=urllib.unquote_plus(params['link']))
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=urllib.unquote_plus(params['link']), listitem=listitem, isFolder=False)

xbmcplugin.endOfDirectory(int(sys.argv[1]))
