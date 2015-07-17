#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
# maintainer: einfall, mod by schomi@vuplus-support.org
#
#This plugin is free software, you are allowed to
#modify it (if you keep the license),
#but you are not allowed to distribute/publish
#it without source code (this version and your modifications).
#This means you also have to distribute
#source code of your modifications.
#######################################################################

from Plugins.Plugin import PluginDescriptor
from Components.ActionMap import *
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmap, MultiContentEntryPixmapAlphaTest
from Components.Pixmap import Pixmap
from Components.AVSwitch import AVSwitch
from Components.PluginComponent import plugins
from Components.config import *
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.ScrollLabel import ScrollLabel
# from Components.FileList import FileList
from re import compile as re_compile
from os import path as os_path, listdir
from Components.MenuList import MenuList
from Components.Harddisk import harddiskmanager
from Tools.Directories import SCOPE_CURRENT_SKIN, resolveFilename, fileExists
from enigma import RT_HALIGN_LEFT, eListboxPythonMultiContent, eServiceReference, eServiceCenter, gFont
from Tools.LoadPixmap import LoadPixmap
from Screens.EpgSelection import EPGSelection
from Screens.ChannelSelection import SimpleChannelSelection
from ServiceReference import ServiceReference
#
from Screens.Screen import Screen
from Screens.InfoBar import MoviePlayer
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.GUIComponent import GUIComponent
from Components.Sources.List import List
from Tools.LoadPixmap import LoadPixmap
from Tools.BoundFunction import boundFunction
from Tools.Directories import pathExists, fileExists, SCOPE_SKIN_IMAGE, resolveFilename
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from enigma import eListboxPythonMultiContent, eListbox, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, loadPNG, RT_WRAP, eConsoleAppContainer, eServiceCenter, eServiceReference, getDesktop, loadPic, loadJPG, RT_VALIGN_CENTER, gPixmapPtr, ePicLoad, eTimer
import sys, os, re, shutil, json
import skin
from os import path, remove
from twisted.web.client import getPage
from twisted.web.client import downloadPage
from twisted.web import client, error as weberror
from twisted.internet import reactor
from twisted.internet import defer
from urllib import urlencode
from __init__ import _

pname = _("TMDb")
pdesc = _("TMDb ... function for Movielist")
pversion = "0.6-r0"
pdate = "20150514"

config.plugins.tmdb = ConfigSubsection()
config.plugins.tmdb.themoviedb_coversize = ConfigSelection(default="w185", choices = ["w92", "w185", "w500", "original"])
config.plugins.tmdb.firsthit = ConfigYesNo(default = False)
config.plugins.tmdb.lang = ConfigSelection(default="de", choices = ["de", "en"])

def cleanFile(text):
	cutlist = ['x264','720p','1080p','1080i','PAL','GERMAN','ENGLiSH','WS','DVDRiP','UNRATED','RETAIL','Web-DL','DL','LD','MiC','MD','DVDR','BDRiP','BLURAY','DTS','UNCUT','ANiME',
				'AC3MD','AC3','AC3D','TS','DVDSCR','COMPLETE','INTERNAL','DTSD','XViD','DIVX','DUBBED','LINE.DUBBED','DD51','DVDR9','DVDR5','h264','AVC',
				'WEBHDTVRiP','WEBHDRiP','WEBRiP','WEBHDTV','WebHD','HDTVRiP','HDRiP','HDTV','ITUNESHD','REPACK','SYNC']
	text = text.replace('.wmv','').replace('.flv','').replace('.ts','').replace('.m2ts','').replace('.mkv','').replace('.avi','').replace('.mpeg','').replace('.mpg','').replace('.iso','')
	
	for word in cutlist:
		text = re.sub('(\_|\-|\.|\+)'+word+'(\_|\-|\.|\+)','+', text, flags=re.I)
	text = text.replace('.',' ').replace('-',' ').replace('_',' ').replace('+','')

	return text
	
def cleanEnd(text):
	text = text.replace('.wmv','').replace('.flv','').replace('.ts','').replace('.m2ts','').replace('.mkv','').replace('.avi','').replace('.mpeg','').replace('.mpg','').replace('.iso','').replace('.mp4','')
	return text
	
class PicLoader:
    def __init__(self, width, height, sc=None):
        self.picload = ePicLoad()
        if(not sc):
            sc = AVSwitch().getFramebufferScale()
        self.picload.setPara((width, height, sc[0], sc[1], False, 1, "#ff000000"))

    def load(self, filename):
        self.picload.startDecode(filename, 0, 0, False)
        data = self.picload.getData()
        return data
    
    def destroy(self):
        del self.picload

class createList(GUIComponent, object):
	GUI_WIDGET = eListbox
	
	def __init__(self, mode):
		GUIComponent.__init__(self)
		self.mode = mode
		self.l = eListboxPythonMultiContent()
#		self.l.setFont(0, gFont('Regular', 22))
		font, size = skin.parameters.get("TMDbListFont", ('Regular', 23))
		self.l.setFont(0, gFont(font, size))
		self.l.setItemHeight(30)
		self.l.setBuildFunc(self.buildList)

	def buildList(self, entry):
		if self.mode == 0:
			width = self.l.getItemSize().width()
			(title, coverUrl, url, id) = entry
			res = [ None ]
			x,y,w,h = skin.parameters.get("TMDbListName", (5,1,1920,30))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT, str(title)))
			#res.append((eListboxPythonMultiContent.TYPE_TEXT, 10, 0, 800, 30, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, str(title)))
			return res

	def getCurrent(self):
		cur = self.l.getCurrentSelection()
		return cur and cur[0]

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		self.instance.setWrapAround(True)

	def preWidgetRemove(self, instance):
		instance.setContent(None)

	def setList(self, list):
		self.l.setList(list)

	def moveToIndex(self, idx):
		self.instance.moveSelectionTo(idx)

	def getSelectionIndex(self):
		return self.l.getCurrentSelectionIndex()

	def getSelectedIndex(self):
		return self.l.getCurrentSelectionIndex()

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)

	def pageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)

	def pageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)

	def up(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)

	def down(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)
		
class tmdbConfigScreen(Screen, ConfigListScreen):
	skin = """
		<screen position="40,80" size="1200,600" title="TMDb - The Movie Database" >
			<widget name="info" position="20,10" size="1170,30" font="Regular;24" foregroundColor="#00fff000"/>
			<widget name="config" position="20,60" size="1170,480" transparent="1" scrollbarMode="showOnDemand" />
			<widget name="key_red" position="100,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_green" position="395,570" size="260,25"  transparent="1" font="Regular;20"/>
			<widget name="key_yellow" position="690,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_blue" position="985,570" size="260,25" transparent="1" font="Regular;20"/>
			<ePixmap position="70,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/button_red.png" transparent="1" alphatest="on"/>
			<ePixmap position="365,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/button_green.png" transparent="1" alphatest="on"/>
			<ePixmap position="660,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/button_yellow.png" transparent="1" alphatest="on"/>
			<ePixmap position="955,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/button_blue.png" transparent="1" alphatest="on"/>
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session

		self["actions"]  = ActionMap(["OkCancelActions", "ShortcutActions", "WizardActions", "ColorActions", "SetupActions", "NumberActions", "MenuActions", "EPGSelectActions"], {
			"cancel": self.cancel,
			"red": self.cancel,
			"green"	: self.save
		}, -1)

		self['info'] = Label(_("Setup"))
		self['key_red'] = Label(_("Cancel"))
		self['key_green'] = Label("Ok")
		self['key_yellow'] = Label(" ")
		self['key_blue'] = Label(" ")

		self.list = []
		self.createConfigList()
		ConfigListScreen.__init__(self, self.list)

	def createConfigList(self):
		self.setTitle("TMDb - The Movie Database v"+pversion)
		self.list = []
		self.list.append(getConfigListEntry(_("Cover resolution:"), config.plugins.tmdb.themoviedb_coversize))
		self.list.append(getConfigListEntry(_("Show first search result:"), config.plugins.tmdb.firsthit))
		self.list.append(getConfigListEntry(_("Language:"), config.plugins.tmdb.lang))

	def changedEntry(self):
		self.createConfigList()
		self["config"].setList(self.list)

	def save(self):
		config.plugins.tmdb.themoviedb_coversize.save()
		config.plugins.tmdb.firsthit.save()
		config.plugins.tmdb.lang.save()
		configfile.save()
		self.close()

	def cancel(self):
		self.close()
		
class tmdbScreen(Screen):
	skin = """
		<screen position="40,80" size="1200,600" title="TMDb - The Movie Database" >
			<widget name="searchinfo" position="20,10" size="1180,30" font="Regular;24" foregroundColor="#00fff000"/>
			<widget name="list" position="10,60" size="800,480" scrollbarMode="showOnDemand"/>
			<widget name="cover" position="840,115" size="300,420" alphatest="blend"/>
			<widget name="key_red" position="100,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_green" position="395,570" size="260,25"  transparent="1" font="Regular;20"/>
			<widget name="key_yellow" position="690,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_blue" position="985,570" size="260,25" transparent="1" font="Regular;20"/>
			<ePixmap position="70,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/button_red.png" transparent="1" alphatest="on"/>
			<ePixmap position="365,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/button_green.png" transparent="1" alphatest="on"/>
			<ePixmap position="660,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/button_yellow.png" transparent="1" alphatest="on"/>
			<ePixmap position="955,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/button_blue.png" transparent="1" alphatest="on"/>
		</screen>"""	

	def __init__(self, session, service, mode):
		Screen.__init__(self, session)
		self.session = session
		self.mode = mode
		self.saveFilename = ""
		
		if self.mode == 1:
			self.isDirectory = False
			serviceHandler = eServiceCenter.getInstance()
			info = serviceHandler.info(service)
			path = service.getPath()
			self.savePath = path
			self.dir = '/'.join(path.split('/')[:-1]) + '/'
			self.file = self.baseName(path)
			if path.endswith("/") is True:
				path = path[:-1]
				self.file = self.baseName(path)
				self.text = self.baseName(path)
				self.isDirectory = True
			else:
				self.text = cleanFile(info.getName(service))
				self.saveFilename = path
				self.isDirectory = False
		else:
			self.text = service
		
		print "[TMDb] " + str(self.text)
		
		self["actions"]  = ActionMap(["OkCancelActions", "ShortcutActions", "WizardActions", "ColorActions", "SetupActions", "NumberActions", "MenuActions", "EPGSelectActions"], {
			"ok": self.ok,
			"cancel": self.cancel,
			"left"  : self.keyLeft,
			"right" : self.keyRight,
			"up"    : self.keyUp,
			"down"  : self.keyDown,
			"green" : self.keyGreen,
			"blue"	: self.keyBlue
		}, -1)

		self['searchinfo'] = Label(_("Loading..."))
		self['key_red'] = Label(_("Exit"))
		self['key_green'] = Label(_("Edit"))
		self['key_yellow'] = Label(_(" "))
		self['key_blue'] = Label(_("Setup"))
		self['list'] = createList(0)
		
		self['cover'] = Pixmap()
		
		self.tempDir = "/var/volatile/tmp/"
		self.onLayoutFinish.append(self.onFinish)
		
	def onFinish(self):
		self.tmdbSeach()

	def tmdbSeach(self):
		self['searchinfo'].setText(_("Try to find %s in tmdb ...") % self.text)
		url = "http://api.themoviedb.org/3/search/movie?api_key=8789cfd3fbab7dccf1269c3d7d867aff&query=%s&language=%s" % (self.text.replace(' ','%20'), config.plugins.tmdb.lang.value)
		print "[TMDb] " + url
		getPage(url, headers={'Content-Type':'application/x-www-form-urlencoded'}).addCallback(self.getResults).addErrback(self.dataError)

	def openMovie(self, data, title, url, cover, id):
		print "Oopen Moviieeeee..."
		self.session.openWithCallback(self.exit, tmdbScreenMovie, title, url, cover, id, self.saveFilename)

	def getResults(self, data):
		if config.plugins.tmdb.firsthit.value:
			list = re.findall('"id":(.*?),.*?original_title":"(.*?)".*?"poster_path":"(.*?)".*?title":"(.*?)"', data, re.S)
			if list:
				for id,otitle,coverPath,title in list:
					url_cover = "http://image.tmdb.org/t/p/%s%s" % (config.plugins.tmdb.themoviedb_coversize.value, coverPath)
					url = "http://api.themoviedb.org/3/movie/%s?api_key=8789cfd3fbab7dccf1269c3d7d867aff&append_to_response=releases,trailers,casts&language=%s" % (id, config.plugins.tmdb.lang.value)
					cover = self.tempDir+id+".jpg"
					downloadPage(url_cover, cover).addCallback(self.openMovie, title, url, cover, id).addErrback(self.dataError)
					break
			else:
				print "[TMDb] no movie found."
				self['searchinfo'].setText(_("No Movie information found for %s") % self.text)
		else:
			urls = []
			list = re.findall('"id":(.*?),.*?original_title":"(.*?)".*?"poster_path":"(.*?)".*?title":"(.*?)"', data, re.S)
			if list:
				for id,otitle,coverPath,title in list:
					url_cover = "http://image.tmdb.org/t/p/%s%s" % (config.plugins.tmdb.themoviedb_coversize.value, coverPath)
					url = "http://api.themoviedb.org/3/movie/%s?api_key=8789cfd3fbab7dccf1269c3d7d867aff&append_to_response=releases,trailers,casts&language=%s" % (id, config.plugins.tmdb.lang.value)
					#print "[tmbd] " + title, url_cover, "\n", url
					urls.append(((title, url_cover, url, id),))
				self['list'].setList(urls)
				self.getInfo()
			else:
				print "[TMDb] no movie found."
				self['searchinfo'].setText(_("No Movie information found for %s") % self.text)

	def getInfo(self):
		url_cover = self['list'].getCurrent()[1]
		id = self['list'].getCurrent()[3]
		
		if not fileExists(self.tempDir+id+".jpg"):
			downloadPage(url_cover, self.tempDir+id+".jpg").addCallback(self.getData, self.tempDir+id+".jpg").addErrback(self.dataError)
		else:
			self.showCover(self.tempDir+id+".jpg")

	def getData(self, data, coverSaved):
		print coverSaved
		self.showCover(coverSaved)

	def dataError(self, error):
		print error

	def baseName(self, str):
		name = str.split('/')[-1]
		return name
			
	def showCover(self, coverName):
		self.picload = ePicLoad()
		if not fileExists(coverName):
			coverName = "/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/no_cover.png"

		if fileExists(coverName):
			self['cover'].instance.setPixmap(gPixmapPtr())
			scale = AVSwitch().getFramebufferScale()
			size = self['cover'].instance.size()
			self.picload.setPara((size.width(), size.height(), scale[0], scale[1], False, 1, "#FF000000"))
			if self.picload.startDecode(coverName, 0, 0, False) == 0:
				ptr = self.picload.getData()
				if ptr != None:
					self['cover'].instance.setPixmap(ptr)
					self['cover'].show()
			del self.picload

	def ok(self):
		check = self['list'].getCurrent()
		if check == None:
			return

		# title, url_cover, url, id
		title =  self['list'].getCurrent()[0]
		url = self['list'].getCurrent()[2]
		id = self['list'].getCurrent()[3]
		cover = self.tempDir+id+".jpg"
		
		print title, url, cover, id
		self.session.open(tmdbScreenMovie, title, url, cover, id, self.saveFilename)

	def keyLeft(self):
		check = self['list'].getCurrent()
		if check == None:
			return
		self['list'].pageUp()
		self.getInfo()

	def keyRight(self):
		check = self['list'].getCurrent()
		if check == None:
			return
		self['list'].pageDown()
		self.getInfo()

	def keyDown(self):
		check = self['list'].getCurrent()
		if check == None:
			return
		self['list'].down()
		self.getInfo()

	def keyUp(self):
		check = self['list'].getCurrent()
		if check == None:
			return
		self['list'].up()
		self.getInfo()

	def keyBlue(self):
		self.session.open(tmdbConfigScreen)

	def keyGreen(self):
		self.session.openWithCallback(self.goSearch, VirtualKeyBoard, title = (_("Search for Movie:")), text = self.text)

	def goSearch(self, newTitle):
		if newTitle is not None:
			self.text = newTitle
			self.tmdbSeach()
		else:
			self.tmdbSeach()

	def exit(self, which):
		if which:
			self.cancel()
		else:
			self.keyGreen()

	def cancel(self):
		self.close()

class tmdbScreenMovie(Screen):
	skin = """
		<screen position="40,80" size="1200,600" title="TMDb - The Movie Database" >
			<widget name="searchinfo" position="10,10" size="930,30" font="Regular;24" foregroundColor="#00fff000"/>
			<widget name="fulldescription" position="10,60" size="620,490" font="Regular;22"/>
			<widget name="cover" position="950,10" size="225,315" alphatest="blend"/>
			<ePixmap position="705,60" size="100,75" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/star.png" transparent="1" alphatest="blend"/>
			<widget name="rating" position="680,90" size="150,25" zPosition="2" transparent="1" font="Regular;22" foregroundColor="black" halign="center"/>
			<widget name="votes_brackets" position="680,145" size="150,25" zPosition="2" transparent="1" font="Regular;22" halign="center"/>
			<widget name="fsk" position="680,175" size="150,25" zPosition="2" transparent="1" font="Regular;22" halign="center"/>
			
			<widget name="year_txt" position="650,220" size="400,25" zPosition="2" transparent="1" font="Regular;22"/>
			<widget name="year" position="780,220" size="400,25" zPosition="2" transparent="1" font="Regular;22"/>
			<widget name="country_txt" position="650,250" size="400,25" zPosition="2" transparent="1" font="Regular;22"/>
			<widget name="country" position="780,250" size="400,25" zPosition="2" transparent="1" font="Regular;22"/>
			<widget name="runtime_txt" position="650,280" size="400,25" zPosition="2" transparent="1" font="Regular;22"/>
			<widget name="runtime" position="780,280" size="400,25" zPosition="2" transparent="1" font="Regular;22"/>
			<widget name="votes_txt" position="650,310" size="400,25" zPosition="2" transparent="1" font="Regular;22"/>
			<widget name="votes" position="780,310" size="400,25" zPosition="2" transparent="1" font="Regular;22"/>
			<widget name="director_txt" position="650,340" size="400,25" zPosition="2" transparent="1" font="Regular;22"/>
			<widget name="director" position="780,340" size="400,25" zPosition="2" transparent="1" font="Regular;22"/>
			<widget name="author_txt" position="650,370" size="400,25" zPosition="2" transparent="1" font="Regular;22"/>
			<widget name="author" position="780,370" size="400,25" zPosition="2" transparent="1" font="Regular;22"/>
			<widget name="genre_txt" position="650,400" size="100,30" font="Regular; 22"/>
			<widget name="genre" position="780,400" size="400,25" zPosition="2" transparent="1" font="Regular;22"/>
			<widget name="studio_txt" position="650,430" size="100,30" font="Regular; 22"/>
			<widget name="studio" position="780,430" size="400,25" zPosition="2" transparent="1" font="Regular;22"/>
			<widget name="subtitle" position="650,460" size="400,25" zPosition="2" transparent="1" font="Regular;22" foregroundColor="#00fff000"/>			
			<widget name="description" position="650,490" size="550,60" zPosition="2" transparent="1" font="Regular;22"/>
			
			<widget name="key_red" position="100,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_green" position="395,570" size="260,25"  transparent="1" font="Regular;20"/>
			<widget name="key_yellow" position="690,570" size="260,25" transparent="1" font="Regular;20"/>
			<widget name="key_blue" position="985,570" size="260,25" transparent="1" font="Regular;20"/>
			<ePixmap position="70,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/button_red.png" transparent="1" alphatest="on"/>
			<ePixmap position="365,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/button_green.png" transparent="1" alphatest="on"/>
			<ePixmap position="660,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/button_yellow.png" transparent="1" alphatest="on"/>
			<ePixmap position="955,570" size="260,25" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/button_blue.png" transparent="1" alphatest="on"/>
		</screen>"""	

	def __init__(self, session, mname, url, coverName, id, saveFilename):
		Screen.__init__(self, session)
		self.session = session
		self.mname = mname
		self.url = url
		self.coverName = coverName
		self.trailer = None
		self.id = id
		self.saveFilename = saveFilename

		self["actions"]  = ActionMap(["OkCancelActions", "ShortcutActions", "WizardActions", "ColorActions", "SetupActions", "NumberActions", "MenuActions", "EPGSelectActions"], {
			#"ok": self.ok,
			"cancel": self.cancel,
			"green" : self.keyGreen,
			"yellow": self.keyYellow,
			"blue"	: self.keyBlue,
			"left"  : self.keyLeft,
			"right" : self.keyRight,
			"up"    : self.keyLeft,
			"down"  : self.keyRight,
			"info"  : self.writeTofile
		}, -1)

		self['searchinfo'] = Label(_("Load Movie information for %s") % self.mname)
		self['genre'] = Label("-")
		self['genre_txt'] = Label(_("Genre:"))
		self['description'] = ScrollLabel("")
		self['fulldescription'] = ScrollLabel("")
		self['rating'] = Label("0.0")
		self['votes'] = Label("-")
		self['votes_brackets'] = Label("")
		self['votes_txt'] = Label(_("Votes:"))
		self['runtime'] = Label("-")
		self['runtime_txt'] = Label(_("Runtime:"))		
		self['fsk'] = Label("FSK: ?")
		self['subtitle'] = Label("-")
		self['year'] = Label("-")
		self['year_txt'] = Label(_("Year:"))
		self['country'] = Label("-")
		self['country_txt'] = Label(_("Countries:"))
		self['director'] = Label("-")
		self['director_txt'] = Label(_("Director:"))
		self['author'] = Label("-")
		self['author_txt'] = Label(_("Author:"))
		self['studio'] = Label("-")
		self['studio_txt'] = Label(_("Studio:"))
		self['key_red'] = Label(_("Exit"))
		self['key_green'] = Label(_("Edit"))
		self['key_yellow'] = Label(_(" "))
		self['key_blue'] = Label(_("Setup"))
		self['cover'] = Pixmap()
		
		self.onLayoutFinish.append(self.onFinish)
		
	def onFinish(self):
		# FSK search
		self.urlfsk = "https://fsk.blacksn0w.de/api/tmdb_id/"+str(self.id)
		print "[TMDb] FSK URL: %s" % self.urlfsk
		getPage(self.urlfsk, headers={'Content-Type':'application/x-www-form-urlencoded'}).addCallback(self.getDataFSK).addErrback(self.dataError)
		# TMDb read
		print "[TMDb] Movie: %s" % self.mname
		print "[TMDb] URL: %s" % self.url
		self['searchinfo'].setText(_("Load Movie information for %s") % self.mname)
		#self.setTitle(self.mname)
		self.showCover(self.coverName)
		getPage(self.url, headers={'Content-Type':'application/x-www-form-urlencoded'}).addCallback(self.getData).addErrback(self.dataError)
		
	def keyLeft(self):
		self['description'].pageUp()
		self['fulldescription'].pageUp()
	def keyRight(self):
		self['description'].pageDown()
		self['fulldescription'].pageDown()

		
	def getDataFSK(self, data):
		# https://fsk.blacksn0w.de/api/tmdb_id/000(Die Nullen sind durch die enstprechende ID zu ersetzen)
		# Antwort:
		# 0 - Freigegeben ab 0
		# 6 - Freigegeben ab 6
		# 12 - Freigegeben ab 12
		# 16 - Freigegeben ab 16
		# 18 - Freigegeben 18
		# 100 - Film nicht in der Datenbank vorhanden
		# 200 - Der Film wurde (noch) nicht von der FSK eingestuft
		# 300 - Falsches Format der übergebenen ID	
		json_data = json.loads(data)
		print "[TMDb] FSK URL: %s" % json_data
		if json_data <=99:
			self['fsk'].setText("FSK: %s" % str(json_data))	
		else:
			self['fsk'].setText("FSK: -")
		
	def getData(self, data):
		# Load json
		json_data = json.loads(data)
		#print json_data
		
		## Year
		if json_data['release_date']:
			year = json_data['release_date'][:+4]
			self['searchinfo'].setText("%s" % self.mname)
			self['year'].setText("%s" % str(year))
			
		## Rating
		vote_average = ""
		if json_data['vote_average']:
			vote_average = json_data['vote_average']
			self['rating'].setText("%s" % str(vote_average))

		## Votes
		vote_count = ""
		if json_data['vote_count']:
			vote_count = json_data['vote_count']
			self['votes'].setText("%s" % str(vote_count))
			self['votes_brackets'].setText("(%s)" % str(vote_count))

		## Runtime
		runtime = ""
		if json_data['runtime']:
			runtime = json_data['runtime']
			self['runtime'].setText("%s min." % str(runtime))
			runtime = ", " + str(runtime) + " min."

		## Country
		country_string = ""
		if json_data['production_countries']:
			for country in json_data['production_countries']:
				country_string += country['iso_3166_1']+"/"
			country_string = country_string[:-1]
			#print country_string
			self['country'].setText("%s" % str(country_string))
			
		## Genre"
		genre_string = ""
		if json_data['genres']:
			genre_count = len(json_data['genres'])
			for genre in json_data['genres']:
				genre_string += genre['name']+", "
			#print genre_string
			self['genre'].setText("%s" % str(genre_string[:-2]))
				
		## Subtitle
		subtitle = ""
		if json_data['tagline']:
			subtitle = json_data['tagline']
			#print subtitle
			self['subtitle'].setText("%s" % str(subtitle))
			subtitle = str(subtitle) + "\n"

		## Cast
		cast_string = ""
		if json_data['casts']['cast']:
			for cast in json_data['casts']['cast']:
				cast_string += cast['name']+" ("+ cast['character'] + ")\n"
			#print cast_string
			
		## Crew
		crew_string = ""
		director = ""
		author = ""
		if json_data['casts']['crew']:
			for crew in json_data['casts']['crew']:

# Translation of Jobs???			
#				if crew['job'] == "Author":
#					crew_string += crew['name']+" ("+ _("Author") + ")\n"
#				elif crew['job'] == "Director":
#					crew_string += crew['name']+" ("+ _("Director") + ")\n"
#				elif crew['job'] == "Music":
#					crew_string += crew['name']+" ("+ _("Music") + ")\n"
#				elif crew['job'] == "Producer":
#					crew_string += crew['name']+" ("+ _("Producer") + ")\n"
#				else:
#					crew_string += crew['name']+" ("+ crew['job'] + ")\n"
#				elif crew['job'] == "Screenplay":
#					crew_string += crew['name']+" ("+ _("Screenplay") + ")\n"

				crew_string += crew['name']+" ("+ crew['job'] + ")\n"
				
				if crew['job'] == "Director":
					director += crew['name']+", "
				if crew['job'] == "Screenplay" or crew['job'] == "Writer":
					author += crew['name']+", "
			#print crew_string
			director = director[:-2]
			author = author[:-2]
			self['director'].setText("%s" % str(director))
			self['author'].setText("%s" % str(author))
			
		## Studio/Production Company
		studio_string = ""
		if json_data['production_companies']:
			for studio in json_data['production_companies']:
				studio_string += studio['name'] +", "
			#print studio_string
			studio_string = studio_string[:-2]
			self['studio'].setText("%s" % str(studio_string))

		## Description
		description = ""
		if json_data['overview']:
			description = json_data['overview']
			description = description + "\n\n" + cast_string + "\n" + crew_string
			self['description'].setText("%s" % description.encode('utf_8','ignore'))
			
			movieinfo ="%s%s %s%s" % (str(genre_string), str(country_string), str(year), str(runtime))
			fulldescription = subtitle + movieinfo + "\n\n" + description
			self['fulldescription'].setText("%s" % fulldescription.encode('utf_8','ignore'))
			self.text = fulldescription

		# Trailer
		if json_data['trailers']['youtube']:
			for trailer in json_data['trailers']['youtube']:
				y_url = "http://www.youtube.com/watch/index.php?v=%s" % str(trailer['source'])
				print "[TMDb] Trailor %s: " % y_url
				self['key_yellow'].setText("Trailer")
				self.trailer = y_url
				#getPage(y_url, headers={'Content-Type':'application/x-www-form-urlencoded'}).addCallback(self.getYoutubeLink).addErrback(self.dataError)
				break
		else:
			print "[TMDb] no trailer found !"

#	def getYoutubeLink(self, data):
#		print "[TMDb] found youtube trailer.."
#		links = re.findall('<a target="_blank" download =".*?" href="(.*?)">(.*?)</a>', data, re.S)
#		if links:
#			for t_url, t_reso in links:
#				self['key_yellow'].setText("Trailer")
#				self.trailer = t_url
#				break			
			
	def dataError(self, error):
		print error

	def showCover(self, coverName):
		self.picload = ePicLoad()
		if not fileExists(coverName):
			coverName = "/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/no_cover.png"

		if fileExists(coverName):
			self['cover'].instance.setPixmap(gPixmapPtr())
			scale = AVSwitch().getFramebufferScale()
			size = self['cover'].instance.size()
			self.picload.setPara((size.width(), size.height(), scale[0], scale[1], False, 1, "#FF000000"))
			if self.picload.startDecode(coverName, 0, 0, False) == 0:
				ptr = self.picload.getData()
				if ptr != None:
					self['cover'].instance.setPixmap(ptr)
					self['cover'].show()
			del self.picload

	def keyBlue(self):
		self.session.open(tmdbConfigScreen)

	def keyYellow(self):
		if self.trailer:
			sref = eServiceReference(0x1001, 0, "http://www.youtube.com/watch?v=qXSPhwYBqZo")
			#sref = eServiceReference(0x1001, 0, self.trailer)
			self.session.open(MoviePlayer, sref)

	def keyGreen(self):
		self.close(False)

	def cancel(self):
		self.close(True)

	def writeTofile(self):
		if not self.saveFilename == "":
			self.session.openWithCallback(self.createTXT, MessageBox, _("Write TMDb Information?"), MessageBox.TYPE_YESNO, default = False)
			
	def createTXT(self, result):
		if result:
			wFile = open(self.saveFilename+".txt","w") 
			wFile.write(self.text) 
			wFile.close()
			print "[TMDb] %s.txt created" % (self.saveFilename)
			self.session.open(MessageBox, _("TMDb information created!"), type = 1, timeout = 5)
			self.session.openWithCallback(self.deleteEIT, MessageBox, _("Delete EIT file?"), MessageBox.TYPE_YESNO, default = False)

	def deleteEIT(self, result):
		if result:
			eitFile = cleanEnd(self.saveFilename)+".eit"
			container = eConsoleAppContainer()
			container.execute("rm -rf '%s'" % eitFile)
			print "[TMDb] %s deleted" % (eitFile)
			self.session.open(MessageBox, _("EIT file deleted!"), type = 1, timeout = 5)
			