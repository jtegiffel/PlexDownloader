#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Ilyaz <>
# URL: https://github.com/ilyaz/PlexDownloader
#
# This file is part of PlexDownloader.
#
# PlexDownlaoder is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PlexDownloader is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PlexDownloader.  If not, see <http://www.gnu.org/licenses/>.
#

from xml.dom import minidom
import urllib
import os
import time
import hashlib
from ConfigParser import SafeConfigParser
import re
import socket
from urllib2 import Request, urlopen, quote
import base64
import uuid
import platform
from time import gmtime, strftime
import random
import string
from myplex import myPlexSignin

parser = SafeConfigParser()
parser.read('user.ini')

sleepTime = parser.get('general', 'sleeptime')
sleepTime = int(sleepTime)
url = parser.get('general', 'plexurl')

myplexstatus = parser.get('myplex', 'status')
myplexusername = parser.get('myplex', 'username')
myplexpassword = parser.get('myplex', 'password')

tvshowid = parser.get('tvshows', 'plexid')
tvfile = parser.get('tvshows', 'tvfile')
tvtype = parser.get('tvshows', 'tvtype')
tvlocation = parser.get('tvshows', 'tvlocation')
tvsync = parser.get('tvshows', 'fullsync')
tvactive = parser.get('tvshows', 'active')
tvdelete = parser.get('tvshows', 'autodelete')
tvunwatched= parser.get('tvshows','unwatched')

tvtranscode= parser.get('tvtranscode','active')
tvheight = parser.get('tvtranscode','height')
tvwidth = parser.get('tvtranscode','width')
tvbitrate = parser.get('tvtranscode','maxbitrate')
tvquality = parser.get('tvtranscode','videoquality')

movietranscode = parser.get('movietranscode','active')
movieheight = parser.get('movietranscode','height')
moviewidth = parser.get('movietranscode','width')
moviebitrate = parser.get('movietranscode','maxbitrate')
moviequality = parser.get('movietranscode','videoquality')

movieid = parser.get('movies', 'plexid')
movielocation = parser.get('movies', 'movielocation')
moviefile = parser.get('movies', 'moviefile')
moviesync = parser.get('movies', 'fullsync')
movieactive = parser.get('movies', 'active')
movieunwatched = parser.get('movies','unwatched')

musicid = parser.get('music', 'plexid')
musiclocation = parser.get('music', 'musiclocation')
musicfile = parser.get('music', 'musicfile')
musicsync = parser.get('music', 'fullsync')
musicactive = parser.get('music', 'active')

pictureid = parser.get('pictures', 'plexid')
picturelocation = parser.get('pictures', 'picturelocation')
picturefile = parser.get('pictures', 'picturefile')
picturesync = parser.get('pictures', 'fullsync')
pictureactive = parser.get('pictures', 'active')

moviescrapetype = parser.get('scrape', 'moviesearch')
moviescrapelimit = int(parser.get('scrape', 'movielimit'))
tvscrapetype = parser.get('scrape', 'tvsearch')
tvscrapelimit = int(parser.get('scrape', 'tvlimit'))
scrapetimer = int(parser.get('scrape', 'timer'))

debug_limitdld = False      #set to true during development to limit size of downloaded files
debug_outputxml = False     #output relevant XML when exceptions occur
debug_pretenddld = False     #set to true to fake downloading.  connects to Plex but doesn't save the file.
debug_pretendremove = False    #set to true to fake removing files
debug_plexurl = False        #set to true to output plex URL  (caution - will output Plex token)
minimum_to_watch_else_considerd_unwatched = 0.95        #minimum % to have watched an episode otherwise will be marked as unwatched todo: configurable
verbose = 0

plexsession=str(uuid.uuid4())
socket.setdefaulttimeout(180)

plextoken=""

print "PlexScraper - v0.02"

def tvShowScraper(searchtype):
    x=0
    tvopen = open(tvfile,"r")
    tvread = tvopen.read()
    tvlist= tvread.split("\n")
    tvopen.close()
    print str(len(tvlist)-1) + " TV Shows Found in Your Wanted List..."
    if myplexstatus=="enable":
        tvhttp=url+"/library/sections/"+tvshowid+"/"+searchtype+"?X-Plex-Token="+plextoken
    else:
        tvhttp=url+"/library/sections/"+tvshowid+"/"+searchtype
    website = urllib.urlopen(tvhttp)
    xmldoc = minidom.parse(website)
    itemlist = xmldoc.getElementsByTagName('Directory')
    print str(len(itemlist)) + " Total TV Shows Found"
    for item in itemlist:
        tvkey = item.attributes['key'].value
        tvtitle = item.attributes['title'].value
        #tvtitle = re.sub(r'[^\x00-\x7F]+',' ', tvtitle)
        tvtitle = re.sub(r'\&','and', tvtitle)
        if (x <= tvscrapelimit):
            tvlist.append(tvtitle)
        x=x+1
    tvlist = list(set(tvlist))
    tvopen = open(tvfile,"r")
    tvread = tvopen.read()
    while '' in tvlist:
        tvlist.remove('')
    tvopen.close()
    tvopen = open(tvfile,"w+")
    for item in tvlist:
        tvwrite = tvopen.write(item+"\n")
    tvopen.close()



def movieScraper(searchtype):
    movieopen = open(moviefile,"r")
    movieread = movieopen.read()
    movielist= movieread.split("\n")
    movieopen.close()
    moviealreadyinlist = len(movielist)-1
    print str(moviealreadyinlist) + " Movies Found in Your Wanted List..."
    if myplexstatus=="enable":
        moviehttp=url+"/library/sections/"+movieid+"/all?X-Plex-Token="+plextoken
    else:
        moviehttp=url+"/library/sections/"+movieid+"/all"

    
    website = urllib.urlopen(moviehttp)
    xmldoc = minidom.parse(website)
    itemlist = xmldoc.getElementsByTagName('Video')
    found_movies = len(itemlist)
    print str(found_movies) + " Total Movies Found"
    if verbose: print "ini moviescrapelimit " + str(moviescrapelimit)
    movietoscrape = moviescrapelimit
    movietoscrape = moviescrapelimit - moviealreadyinlist
    print "Found " + str(moviescrapelimit) + " movies in your wanted list and moviescraping is set to maximum " + str(moviescrapelimit) + ", movies to add by scraper " + str(movietoscrape)
    random_movie = 0 
    x=1

    while x <= movietoscrape:
        random_movie = random.randrange(0, found_movies, 1)
        item = itemlist[random_movie]
        if verbose: print "Choose random movie:" + (item.attributes['title'].value) # + "\n" +  item.toprettyxml()
        duration = long(item.attributes['duration'].value)
        this_minimum_to_watch = long(duration * minimum_to_watch_else_considerd_unwatched)
        try:
            #checks to see if episode has been viewed node is available
            viewcount = long(itemlist[random_movie].attributes['lastViewedAt'].value)
        except Exception as e:
            #if fails to find lastViewedAt will notify script that tv is unwatched
            viewcount = "unwatched"

        try:
            viewOffset = long(itemlist[random_movie].attributes['viewOffset'].value)
            if verbose: print "    viewOffset: " + str(viewOffset)
            if viewOffset < this_minimum_to_watch: viewcount = "partial"
            #if viewOffset < (duration - 316482) : viewcount = "partial - 5 min"
        except Exception as e:
            #if fails to find viewOffset will notify script that tv is unwatched
            viewOffset = 0
        if verbose: print "    viewcount: " + str(viewcount)
        if verbose: print "    x: " + str(x)
        
        movietitle = item.attributes['title'].value
        #movietitle = re.sub(r'[^\x00-\x7F]+',' ', movietitle)
        movietitle = re.sub(r'\&','and', movietitle)
        moviedata = item.attributes['key'].value
        movieratingkey = item.attributes['ratingKey'].value
        # print (movietitle)
        try:
            movieyear = item.attributes['year'].value
        except:
            movieyear="Unknown"
        moviename = movietitle + " ("+movieyear+")"
        # random_movie = random_movie + 1 # only here for testing purpose
        if debug_outputxml: print item.toprettyxml(encoding='utf-8')
        if movieunwatched !="enable" or (movieunwatched=="enable" and (str(viewcount)=='partial' or str(viewcount)=='unwatched')):
            ## when setting 'movieunwatched' is found only add unwatched or partially watched movies, otherwise add anyway
            print "Adding: " + viewcount + " movie: "+ moviename + "\n"
            movielist.append(moviename)
            x=x+1
        else:
            print "Skipping: watched movie " + moviename + "\n"
        
        ## only touch the movie file when changed by the scraper
        if x>0:
            ## todo: update web page when movie is added
            movielist = list(set(movielist))
            movieopen = open(moviefile,"r")
            movieread = movieopen.read()
            while '' in movielist:
                movielist.remove('')
            movieopen.close()
            movieopen = open(moviefile,"w+")
            for item in movielist:
                moviewrite = movieopen.write(item+"\n")
            movieopen.close()


def photoScraper(searchtype):
    pictureopen = open(picturefile,"r")
    pictureread = pictureopen.read()
    picturelist= pictureread.split("\n")
    pictureopen.close()
    print str(len(picturelist)-1) + " Albums Found in Your Wanted List..."

    if myplexstatus=="enable":
        pichttp=url+"/library/sections/"+pictureid+"/"+searchtype+"?X-Plex-Token="+plextoken
    else:
        pichttp=url+"/library/sections/"+pictureid+"/"+searchtype
    website = urllib.urlopen(pichttp)
    xmldoc = minidom.parse(website)
    itemlist = xmldoc.getElementsByTagName('Directory')
    print str(len(itemlist)) + " Total Albums Found"
    for item in itemlist:
        albumtitle = item.attributes['title'].value
        #albumtitle = re.sub(r'[^\x00-\x7F]+',' ', albumtitle)
        albumtitle = re.sub(r'\&','and', albumtitle)
        albumkey = item.attributes['key'].value




def musicScraper(searchtype):
    musicopen = open(musicfile,"r")
    musicread = musicopen.read()
    musiclist= musicread.split("\n")
    musicopen.close()
    print str(len(musiclist)-1) + " Artists Found in Your Wanted List..."
    if myplexstatus=="enable":
        musichttp=url+"/library/sections/"+musicid+"/"+searchtype+"?X-Plex-Token="+plextoken
    else:
        musichttp=url+"/library/sections/"+musicid+"/"+searchtype
    website = urllib.urlopen(musichttp)
    xmldoc = minidom.parse(website)
    #Get list of artists
    itemlist = xmldoc.getElementsByTagName('Directory')
    print str(len(itemlist)) + " Total Artists Found"
    for item in itemlist:
        musictitle = item.attributes['title'].value
        #musictitle = re.sub(r'[^\x00-\x7F]+',' ', musictitle)
        musictitle = re.sub(r'\&','and', musictitle)
        musickey = item.attributes['key'].value



while True:
    try:
        if myplexstatus=="enable":
            plextoken = myPlexSignin(myplexusername,myplexpassword)
        if myplexstatus=="enable" and plextoken=="":
            print "Failed to login to myPlex. Please disable myPlex or enter your correct login."
            exit()
        if tvactive=="enable" and tvscrapetype != "disable":
            tvShowScraper(tvscrapetype)
        if movieactive=="enable" and moviescrapetype != "disable":
            movieScraper("")
        #if pictureactive=="enable":
        #    photoScraper('recentlyAdded')
        #if musicactive=="enable":
        #    musicScraper('recentlyAdded')

        print "Plex Scraper completed at "+ strftime("%Y-%m-%d %H:%M:%S")
        print "Plex Scraper Sleeping "+str(scrapetimer)+" Seconds..."
        time.sleep(scrapetimer)
    except Exception,e:
        print "Something went wrong: " + str(e)
        print "Plex Scraper failed at "+ strftime("%Y-%m-%d %H:%M:%S")
        print "Retrying in "+str(scrapetimer)+" Seconds..."
        time.sleep(scrapetimer)
