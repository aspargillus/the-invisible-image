#                                                -*- coding: latin-1 -*-
# ii.py - The Invisible Image Browser
#
import sys
import traceback
import os
import os.path
import threading
from time import sleep
import cPickle
import random
import re
import wx
import httplib
import urllib
from urllib2 import urlopen, Request
from datetime import datetime, timedelta
from BeautifulSoup import BeautifulSoup
import Image
import appscript

def GetBitmap(image):
    #rgba = image.convert( "RGBA")
    #r = rgba.split()[0]
    #log('r', r.getextrema())
    #g = rgba.split()[1]
    #log('g', g.getextrema())
    #b = rgba.split()[2]
    #log('b', b.getextrema())
    #a = rgba.split()[3]
    #log('a', a.getextrema())
    ###wxim = apply(wx.EmptyImage, image.size)
    wxim = wx.EmptyImage(*image.size)
    wxim.SetData(image.convert( "RGB").tostring())
    # if the image has an alpha channel, you can set it with this line:
    wxim.SetAlphaData(image.convert("RGBA").tostring()[3::4])
    return wx.BitmapFromImage(wxim)

__logfile = open('ii.log', 'w')
loggers = []
def log_debug(*args):
    s = ' '.join([str(obj) for obj in args])
    #print s
    __logfile.write('[%s]: %s\n' % (threading.currentThread().getName(), s))
    __logfile.flush()
def log(*args):
    s = ' '.join([str(obj) for obj in args])
    #print s
    __logfile.write('[%s]: %s\n' % (threading.currentThread().getName(), s))
    __logfile.flush()
    for l in loggers:
        l.log(s)

def break_url(url, breaks):
    if breaks == 0:
        return [url]
    n = len(url) / (breaks+1)
    o = 3
    while True:
        i = url.find('/', n-o, n+o)
        if i > 0:
            return [url[:i+1] + ' \n', ' ' + url[i+1:]]
        o += 3

class IImage:
    interesting_info = ['dpi', 'software', 'copyright',
                        'author', 'comment', 'version']

    def __init__(self, image_url, reference_url, filename):
        try:
            self.name = os.path.basename(image_url)
            self.filename = filename
            self.url = image_url
            self.refurl = reference_url
            self.image = Image.open(filename)
        except:
            log_debug(traceback.format_exc())

    def mode_string(self):
        if self.image.mode == 'P': return 'Palette'
        if self.image.mode == 'L': return 'Greyscale'
        if self.image.mode == 'RGBA': return 'RGB + Alpha'
        return self.image.mode

    def filesize(self):
        return os.path.getsize(self.filename)

    def extra_info(self):
        return ["%s: %s" % (k, self.image.info[k])
                for k in self.image.info.keys()
                if k.lower() in self.interesting_info]

    def is_transparent(self):
        ## DEBUG
        #return True
        if self.image.mode == 'P':
            (lo, hi) = self.image.getextrema()
            return self.image.info.has_key('transparency') \
               and lo == hi \
                and lo == self.image.info['transparency']
        if self.image.mode == 'RGBA':
            (lo, hi) = self.image.split()[3].getextrema()
            return lo == hi and lo == 0
        return False

    def is_monochrome(self):
        if len(self.image.mode) == 1:
            (h, l) = self.image.getextrema()
            return h == l
        bands = self.image.split()
        types = self.image.getbands()
        for i in range(len(bands)):
            if types[i] == 'A':
                continue
            (h, l) = bands[i].getextrema()
            if h != l:
                return False
        return True

class IICache:
    dir = os.getenv('HOME', '.') + '/__IICache__'

    def __init__(self):
        if not os.path.isdir(self.dir):
            log_debug('IICache: starting with an empty cache.')
            os.mkdir(self.dir)
            self.__index = {}
            self.__visible = []
            return
        try:
            self.__index = cPickle.load(open(self.dir + '/index', 'r'))
            self.__visible = cPickle.load(open(self.dir + '/visible', 'r'))
            log('IICache: initialised normally.')
            log('Index contains %d images, %d are visible.'
                % (len(self.__index), len(self.__visible)))
        except:
            log_debug('IICache: some error occurred initialising the indices:')
            log_debug(traceback.format_exc())
            self.__index = {}
            self.__visible = []
        for url in self.__index.keys():
            if not os.path.isfile(self.__filename(url)):
                log_debug('IICache: file for %s does not exist.'
                          % (self.__filename(url)))
                del self.__index[url]

    def save(self):
        cPickle.dump(self.__index, open(self.dir + '/index', 'w'))
        cPickle.dump(self.__visible, open(self.dir + '/visible', 'w'))

    def size(self):
        return len(self.__index.keys())

    def contents(self):
        return self.__index.keys()

    def get(self, imgurl, refurl):
        #log('IICache.get(%s, %s)' % (imgurl, refurl))
        basename = imgurl.split('/')[-1]
        log('Untersuche Grafik %s...' % imgurl)
        filename = self.__filename(imgurl)

        if imgurl in self.__visible:
            log('  Grafik %s ist als sichtbar im Cache.' % (basename))
            return None

        if self.__index.has_key(imgurl) and os.path.isfile(filename):
            log('  Grafik %s ist im Cache.' % (basename))
            try:
                image = IImage(imgurl, refurl, filename)
                if not image.is_transparent():
                    self.__visible.append(imgurl)
                    log('  Grafik %s ist sichtbar.' % (basename))
                    return None
                return image
            except Exception, e:
                log('Fehler beim Öffnen der Grafik: %s' % str(e))
                return None

        log('GET', imgurl)
        #log('retriving %s to %s' % (imgurl, filename))
        try:
            (filename, headers) = urllib.urlretrieve(imgurl, filename)
        except IOError, e:
            log('Fehlschlag: %s' % (str(e)))
            return None
        #log(headers)
        if not headers.gettype().startswith('image/'):
            log('  %s ist gar keine Grafik!.' % (basename))
            return None
        self.__index[imgurl] = refurl
        try:
            image = IImage(imgurl, refurl, filename)
            if not image.is_transparent():
                log('  Grafik %s ist sichtbar.' % (basename))
                return None
            log('  Grafik %s ist transparent.' % (basename))
            self.save()
            return image
        except Exception, e:
            log('Fehler beim Öffnen der Grafik: %s' % str(e))
            return None

    def __getitem__(self, index):
        imgurl = self.__index.keys()[index]
        try:
            result = IImage(imgurl,
                            self.__index[imgurl], self.__filename(imgurl))
            if result.is_transparent():
                return result
        except Exception, e:
            log('Fehler beim Öffnen der Grafik: %s' % str(e))
        return None

    def __filename(self, url):
        return self.dir + '/' + urllib.quote(url, '')

class NoMoreImages(Exception):
    def str(self):
        return 'Es konnten keine weiteren Grafiken gefunden werden.'

class QueryError(Exception):
    def __init__(self, str):
        Exception.__init__(self, str)

class IIQuery:
    def __init(self):
        pass
    def get_next(self):
        pass
    def finish(self):
        pass

class CacheDummyQuery(IIQuery):
    max_images_from_cache = 20

    def __init__(self, cache):
        #log('CacheDummyQuery()')
        self.cache = cache
        self.index = random.randint(0, max(cache.size() - 1, 1))
        self.counter = 0

    def get_next(self):
        log_debug('images from cache so far: %d' % (self.counter))
        n = self.cache.size()
        if self.counter > min(n, self.max_images_from_cache):
            raise NoMoreImages
        self.counter += 1
        old = self.index
        result = None
        while result is None:
            self.index = (self.index + random.randint(1, n-1)) % n
            result = self.cache[self.index]
        #log("%d: %d -> %d => %s" % (n, old, self.index, result.name))
        return result

class GoogleQuery(IIQuery):
    image_sizes = ['icon', 'small', 'medium', 'large', 'xlarge', 'xxlarge']
    base_url = 'http://images.google.com/images?svnum=10&hl=en&nojs=1&safe=off&btnG=Google+Search'
    #result_src_re = re.compile('^/imgres\\?imgurl=([^&]+)&imgrefurl=([^&]+).*')
    result_src_re = re.compile('^.*imgurl=([^&]+)&imgrefurl=([^&]+).*')
    next_re = re.compile('^/intl/.*/nav_next\\.gif')

    minimum_queue_length = 10
    query_interval = 10

    def __init__(self, pattern='', keywords='', exclude='',
                 site='', filetype='', size='', start=None):
        #log('GoogleQuery(pattern=%s, keywords=%s, exclude=%s, site=%s, filetype=%s, size=%s)' % (pattern, keywords, exclude, site, filetype, size))
        self._offset = start
        self.query_string = self.base_url \
            + '&as_q=%s&as_epq=&as_oq=%s&as_eq=%s&imgsz=%s&as_filetype=%s&imgc=&as_sitesearch=%s' \
            % (keywords, pattern, exclude,
               size or self.image_sizes[0],
               filetype, site)
        log_debug(self.query_string)
        self.__res = []
        self.more_pages = True

        self._error = None
        self._image_queue = []
        self._req_queue = []
        self._query_lock = threading.Lock()
        #self._query_thread = threading.Thread(target=self._fill_image_queue,
        #                                      name='GoogleQuery')
        self._query_thread = threading.Thread(target=self._query_thread_method,
                                              name='GoogleQuery')
        self._query_thread.setDaemon(True)
        self._query_thread_finish = False
        self._query_thread.start()

    # query and image retrieval methods run in a separate thread
    def _query_thread_method(self):
        while self._fill_image_queue() and not self._query_thread_finish:
            log_debug('queue is filled')
            sleep(self.query_interval)
    def _fill_image_queue(self):
        while len(self._image_queue) < self.minimum_queue_length \
                and not self._query_thread_finish:
            log('Brauche mehr Grafiken!')

            try:
                # fill request queue if necessary
                while len(self._req_queue) == 0 \
                        and not self._query_thread_finish:
                    new_images = self._get_more_images()
                    log('  %d Grafiken gefunden' % (len(new_images)))
                    if not new_images:
                        self._error = NoMoreImages()
                        return False
                    # FIXME: better detection needed!
                    if len(new_images) < 20:
                        self._error = NoMoreImages()
                        break
                    self._req_queue += new_images
                    self._offset += len(new_images)
                # now process request queue and fill image queue
                imgurl, refurl = self._req_queue.pop(0)
                image = the_cache.get(imgurl, refurl)
                if image:
                    self._query_lock.acquire()
                    self._image_queue.append(image)
                    self._query_lock.release()
            except Exception, e:
                self._error = QueryError(
                    'Problem beim Runterladen der Grafiken: ' + str(e))
                return False
            #log('*** %d images in the queue! **' % (len(self._image_queue)))
        #log('*** queue is full: %s' % (str(result)))
        return True
    def _get_more_images(self):
        log('Suche bei Google Images.')
        req = Request(
            self.query_string + '&start=%s' % (self._offset),
            headers = {
                'User-Agent':
                'The Invisible Image (http://www.lynix.net/~frank/ii.html)'},
            unverifiable = True)
        try:
            page = urlopen(req)
        except IOError, e:
            self._error = QueryError('Google Images antwortet nicht: ' + str(e))
            return []
        if not page:
            return []
        body = BeautifulSoup(page).body
        return [(re.sub(self.result_src_re, '\\1',
                        t.get('href').encode()),
                 re.sub(self.result_src_re, '\\2',
                        t.get('href').encode()))
                for t in body.findAll('a',
                                      {'href': self.result_src_re})]

    def get_next(self):
        result = None
        if self._query_lock.acquire(False):
            log_debug('GoogleQuery.get_next(): queue length is %d.'
                      % (len(self._image_queue)))
            result = self._get_next()
            #log('get_next() => %s [queue length: %d; query thread alive: %s]'
            #    % (result, len(self._image_queue),
            #       self._query_thread.isAlive()))
            if not self._query_thread.isAlive():
                log('***** Have to restart query thread!')
                del self._query_thread
                self._query_thread = threading.Thread(
                    target=self._fill_image_queue,
                    name='GoogleQuery')
                self._query_thread.start()
            self._query_lock.release()
        else:
            log_debug('GoogleQuery.get_next(): queue is locked.')
            return None
        if result is None and self._error is not None:
            raise self._error
        return result

    def _get_next(self):
        if len(self._image_queue) > 0:
            return self._image_queue.pop(0)
        return None

    def finish(self):
        self._query_thread_finish = True

class Action:
    def __init__(self, interval, once=False):
        self.interval = interval
        self.once = once
    def iterations(self, frame):
        pass
    def step(self, frame, count):
        pass
    def cancel(self):
        pass
    def end_hook(self, frame):
        pass

class DebugAction(Action):
    def __init__(self, *arguments):
        Action.__init__(self, 1, once=True)
        self.args = arguments
    def iterations(self, frame):
        return 1
    def step(self, frame, count):
        #log(self.args)
        return
    def cancel(self):
        return False

class FunctionAction(Action):
    def __init__(self, function, *arguments):
        Action.__init__(self, 1, once=True)
        self.fun=function
        self.args = arguments
    def iterations(self, frame):
        return 1
    def step(self, frame, count):
        f = self.fun
        if f:
            f(*self.args)
    def cancel(self):
        return False

class WaitALittle(Action):
    def __init__(self, interval):
        Action.__init__(self, interval, once=True)
    def iterations(self, frame):
        #log('waiting %g seconds' % (self.interval / 1000.0))
        return 1
    def step(self, frame, count):
        return
    def cancel(self):
        #log('cancelling wait')
        return True

class CrossFadeAction(Action):
    def __init__(self, target_colour, end_state=None):
        Action.__init__(self, 40)
        self.r = target_colour[0]
        self.g = target_colour[1]
        self.b = target_colour[2]
        self.end_state = end_state
    def iterations(self, frame):
        frame.set_state(frame.state_fade)
        bg = frame.get_bg()
        result = max(abs(self.r - bg[0]),
                     abs(self.g - bg[1]),
                     abs(self.b - bg[2]),
                     5)/ 5
        #log('CrossFadeAction.iterations() => %d' % (result))
        return result
    def step(self, frame, count):
        f = 1.0 / max(float(count), 1)
        bg = frame.get_bg()
        frame.set_bg((bg[0] + (self.r - bg[0]) * f,
                      bg[1] + (self.g - bg[1]) * f,
                      bg[2] + (self.b - bg[2]) * f))
    def cancel(self):
        return False
    def end_hook(self, frame):
        if self.end_state is not None:
            frame.set_state(self.end_state)

class TextFadeAction(Action):
    def __init__(self, target_colour):
        Action.__init__(self, 20)
        self.r = target_colour[0]
        self.g = target_colour[1]
        self.b = target_colour[2]
    def iterations(self, frame):
        fg = frame.get_fg()
        result = int(max(abs(self.r - fg[0]),
                         abs(self.g - fg[1]),
                         abs(self.b - fg[2]),
                         8) / 8)
        #log('TextFadeAction.iterations() => %d' % (result))
        return result
    def step(self, frame, count):
        f = 1.0 / float(count)
        fg = frame.get_fg()
        frame.set_fg((fg[0] + (self.r - fg[0]) * f,
                      fg[1] + (self.g - fg[1]) * f,
                      fg[2] + (self.b - fg[2]) * f))
        frame.Refresh()
    def cancel(self):
        return False


class ActionQueue:
    def __init__(self, frame):
        self._q = []
        self._c = 0
        self._t = wx.Timer(frame)
        self._f = frame
        frame.Bind(wx.EVT_TIMER, self.handle_timer)

    def add(self, action):
        #log("ActionQueue.add(%s)" % (action))
        self._q.append(action)
        self.next()

    def flush(self):
        #log("ActionQueue.flush()")
        if len(self._q) == 0:
            return
        self._q = self._q[0:1]
        if self._q[0].cancel():
            self._q = []
            self.next()

    def next(self):
        #log("ActionQueue.next() queue=%d; count=%d, %s" % (len(self._q), self._c, self._t.IsRunning() and 'running' or 'stopped'))
        if len(self._q) == 0:
            #log('ActionQueue.next(): STOPPING queue')
            self._t.Stop()
            return
        if not self._t.IsRunning():
            #log('ActionQueue.next(): starting queue')
            self._c = max(1, self._q[0].iterations(self._f))
            self._t.Start(self._q[0].interval)
            return
        if self._c <= 0:
            #log('ActionQueue.next(): action finished')
            self._t.Stop()
            self._q[0].end_hook(self._f)
            self._q.pop(0)
            if len(self._q) == 0:
                #log('ActionQueue.next(): queue is empty')
                return
            #log('ActionQueue.next(): next action')
            self._c = max(1, self._q[0].iterations(self._f))
            self._t.Start(self._q[0].interval)
            #log("                       queue=%d; count=%d, %s" % (len(self._q), self._c, self._t.IsRunning() and 'running' or 'stopped'))
            return

    def handle_timer(self, event):
        #log("ActionQueue.handle_timer(): %d" % (self._c))
        if len(self._q) == 0:
            log('Ahhhhh! STOPPING (this should never happen...)')
            self._t.Stop()
            return
        self._q[0].step(self._f, self._c)
        self._c -= 1
        self.next()

class IIDisplayFrame(wx.Frame):
    state_proc = 0
    state_info = 1
    state_disp = 2
    state_fade = 3
    states = ['processing', 'info', 'displaying', 'fading']
    spacer_pattern = 'spacer+blank+pixel+clear+1x1+leer+abstand'
    web_bug_patterns = ['pixel cgi',
                        'dot cgi',
                        '"cgi-bin" -counter',
                        'ad/pixel',
                        'ctasp-server.cgi',
                        'cgi-bin/ivw/CP']

    special_query_data = [
        ('Grafiken mit Schreibfehlern im Namen',
         {'pattern': 'sapcer+balnk', 'start': 0}),
        ('Besonders große Grafiken', {'size': 'xlarge|xlarge', 'start': 0}),
        ('Nur PNGs', {'filetype': 'png'}),
        ('Nur GIFs', {'filetype': 'gif'}),
        ('Invisible Austria! (Grafiken von österreichischen Websites)',
         {'size': 'icon', 'site': 'at'}),
        ]

    info_background    = (  0,   0,   0)
    info_foreground    = (255, 255, 255)
    display_background = (255, 255, 255)

    max_heartbeat_interval = 60

    def __init__(self, display=None, debug=False):
        wx.Frame.__init__(self, None, -1,
                          name='The Invisible Image',
                          style=debug and wx.DEFAULT_FRAME_STYLE or wx.NO_BORDER)

        self.panel = wx.Panel(self)
        self.panel.SetFocus()
        self.panel.Bind(wx.EVT_KEY_DOWN, self.handle_key)
        self.panel.Bind(wx.EVT_PAINT, self.handle_paint)

        # set initial frame properties
        if display:
            x, y, w, h = display.GetGeometry()
            #log('setting size: %d %d %d %d' % (x, y, w, h))
            if debug:
                self.SetDimensions(x, y + h/2, w/2, h/2)
            else:
                self.SetDimensions(x, y, w, h)

        from math import sqrt
        w, h = self.GetSizeTuple()
        self.font_size = int(sqrt(w*w + h*h)) / 64
        log_debug('font size: %d' % (self.font_size))

        self.fullscreen = False # NOTE: may be toggled once
        #self.CenterOnScreen()
        #if not debug:
        #    self.toggle_fullscreen()
        self.set_bg(self.info_background)
        self.set_fg(self.info_background)
        self.head_font = wx.Font(self.font_size, wx.SWISS, wx.NORMAL, wx.BOLD)
        self.info_font = wx.Font(self.font_size, wx.SWISS, wx.NORMAL, wx.NORMAL)
        self.progress_font = wx.Font(self.font_size,
                                     wx.TELETYPE, wx.NORMAL, wx.NORMAL)

        # set initial application logic state
        self.state = self.state_proc
        self.actions = ActionQueue(self)
        self.key = 0
        self._image = None
        self._query = None
        self._bitmap = None
        self.errors = 0
        self.empty_queue_counter = 0

        self._special = random.randint(0, len(self.special_query_data))

        self.main_frame = None
        if not debug:
            self._firefox = appscript.app('Firefox')
        else:
            self._firefox = None

        self._watchdog_tread = threading.Thread(target=self._watchdog,
                                                name='watchdog')
        self._heartbeat = datetime.now()
        self._watchdog_tread.setDaemon(True)
        self._watchdog_tread.start()

    def heartbeat(self):
        self._heartbeat = datetime.now()
    def _watchdog(self):
        dt = min(int(self.max_heartbeat_interval / 10), 10)
        while True:
            log_debug('checking heartbeat.')
            log_debug([t.getName() for t in threading.enumerate()])
            if (datetime.now() - self._heartbeat).seconds \
                    > self.max_heartbeat_interval:
                log('******* Woof! Last heartbeat was %d seconds ago!'
                    % (datetime.now() - self._heartbeat).seconds)
                self.query_default()
            sleep(dt)

    def firefox_load_page(self, imgurl, refurl):
        url = '%s?hiliteimg=%s&' % (urllib.quote(refurl, ':/_.'),
                                    urllib.quote(imgurl, ':/_.'))
        if self._firefox:
            self._firefox.Get_URL(url)
    def firefox_show_page(self):
        if self.main_frame:
            self.main_frame.Show(False)
    def firefox_unshow_page(self):
        if self.main_frame:
            self.main_frame.Show(True)

    def set_main_frame(self, main_frame):
        self.main_frame = main_frame
    def set_query(self, name, query):
        if self._query:
            self._query.finish()
        self._query = query
        if getattr(self, 'main_frame', None):
            self.main_frame.set_query(name)

    ## User Interaction
    def force_next_image(self):
        self.actions.flush()
        self.next_image()

    def query_google(self, name,
                     pattern=spacer_pattern,
                     keywords='',
                     exclude='site:blank-wall.com+filetype:jpg',
                     #exclude='filetype:jpg',
                     site='',
                     filetype='',
                     size='icon',
                     start=random.randint(0, 42 * 23) / random.randint(1, 7)):
        self.heartbeat()
        if start is None or site:
            start = 0
        self.set_query(name,
                       GoogleQuery(pattern=pattern, keywords=keywords,
                                   exclude=exclude, site=site,
                                   filetype=filetype, size=size,
                                   start=start))
        self.force_next_image()
    def query_default(self):
        self.query_google('Sonstwas... (uneingeschränkte Suche)')
        return
    def query_cache(self):
        #self.heartbeat()
        self.set_query('Grafiken aus dem Cache',
                       CacheDummyQuery(the_cache))
        self.force_next_image()

    ## Application Logic
    def next_image(self):
        # hide firefox (i.e. unhide main frame)
        self.actions.add(FunctionAction(self.firefox_unshow_page))
        if self.state == self.state_info:
            # fade out info text if showing any
            self.actions.add(DebugAction('fading out info text'))
            self.actions.add(TextFadeAction(self.info_background))
            self.actions.add(FunctionAction(self.set_state, self.state_proc))
        elif self.state == self.state_disp:
            # fade to info background colour if displaying an image
            self.actions.add(DebugAction('fading to proc bg'))
            self.actions.add(CrossFadeAction(self.info_background,
                                             self.state_proc))
        else:
            self.actions.add(FunctionAction(self.set_state, self.state_proc))

        try:
            if not self._query:
                self.query_default()
            image = self._query.get_next()
        except QueryError, e:
            self.errors += 1
            if self.errors > 5:
                log('OK, ich geb\'s auf...')
                self.errors = 0
                self.query_cache()
                return
            log('Le Internet ist broken:')
            log(e)
            #log('Wenn dies oefter vorkommt, druecke "C", um etwas zu sehen.')
            # some problem occured: re-shedule
            self.actions.add(FunctionAction(self.next_image))
            return
        except NoMoreImages:
            log("Es wurden keine weiteren Grafiken gefunden.")
            self.errors += 1
            if self.errors > 5:
                log('OK, ich geb\'s auf...')
                self.errors = 0
                self.query_cache()
                return
            #log("Druecke eine der Tasten fuer eine neue Suche.")
            log("Starte eine neue Suche...")
            self.actions.add(WaitALittle(1000))
            self.actions.add(FunctionAction(self.query_default()))
            return
        except Exception, e:
            log('Hoppla! Da ging etwas schief:', e)
            log_debug(traceback.format_exc())
            self.errors += 1
            if self.errors > 5:
                log('OK, ich geb\'s auf...')
                self.errors = 0
                self.query_cache()
                return
            # some problem occured: re-shedule
            self.actions.add(FunctionAction(self.next_image))
            return

        if image is None:
            # query still under way: re-shedule
            self.empty_queue_counter += 1
            if self.empty_queue_counter > 10:
                log('')
                log('Es gibt derzeit leider keine Treffer für diese Suche.')
                log('')
                self.empty_queue_counter = 0
            self.actions.add(WaitALittle(4000))
            self.actions.add(FunctionAction(self.next_image))
            return

        #log('transparent:', image.is_transparent())
        self.errors = 0
        self.show_image(image)

    def show_image(self, image):
        self.actions.add(DebugAction('show_image(%s). state is %s' % (image.name, self.states[self.state])))

        # load referencing page in firefox, hilighting the spacer
        self.actions.add(FunctionAction(self.firefox_load_page,
                                        image.url, image.refurl))
        # fade to info bg
        self.actions.add(DebugAction('fading to info bg'))
        self.actions.add(CrossFadeAction(self.info_background, self.state_info))
        self.actions.add(WaitALittle(500))
        # fade in info text
        self.actions.add(DebugAction('fading in info text', image.name))
        self.actions.add(FunctionAction(self.set_image, image))
        self.actions.add(TextFadeAction(self.info_foreground))
        self.actions.add(WaitALittle(5000))
        # fade out info text
        self.actions.add(DebugAction('fading out info text'))
        self.actions.add(TextFadeAction(self.info_background))
        self.actions.add(WaitALittle(500))
        # show firefox (layout of referencing page)
        self.actions.add(FunctionAction(self.firefox_show_page))
        # fade to display background colour
        self.actions.add(DebugAction('fading to display bg'))
        self.actions.add(CrossFadeAction(self.display_background,
                                         self.state_disp))
        self.actions.add(FunctionAction(self.display))
        self.actions.add(WaitALittle(15000))
        self.actions.add(FunctionAction(self.loop))

    def loop(self):
        #self._image=None
        #log('loop()')
        self.actions.flush()
        self.actions.add(FunctionAction(self.undisplay))
        self.actions.add(FunctionAction(self.firefox_unshow_page))
        # fade back to info background colour
        self.actions.add(DebugAction('fading to info bg'))
        self.actions.add(CrossFadeAction(self.info_background, self.state_info))
        self.actions.add(FunctionAction(self.next_image()))

    def set_state(self, state):
        self.state = state
        #log('new state: ', self.states[state])
    def set_image(self, image):
        self.heartbeat()
        self._image = image
        log('Zeige Grafik', self._image.name)
    def display(self):
        # actually put the image on the screen!
        #log('display(%s)' % self._image.filename)
        if not self._image:
            return
        self._bitmap = GetBitmap(self._image.image)
        self.Refresh()
    def undisplay(self):
        #log('undisplay()')
        self._bitmap = None
        self._image = None

    ## frame properties
    def get_bg(self):
        bg = self.GetBackgroundColour()
        return (bg.Red(), bg.Green(), bg.Blue())
    def set_bg(self, rgb):
        self.background = rgb
        self.SetBackgroundColour(wx.Colour(rgb[0], rgb[1], rgb[2]))
        #self.ClearBackground()
        self.panel.SetBackgroundColour(wx.Colour(rgb[0], rgb[1], rgb[2]))
        #self.panel.ClearBackground()
    def get_fg(self):
        return self.foreground
    def set_fg(self, rgb):
        self.foreground = rgb

    def toggle_fullscreen(self):
        #print 'toggle_fullscreen()'
        self.fullscreen = not self.fullscreen
        self.ShowFullScreen(self.fullscreen)
        if self.fullscreen:
            self.MoveXY(0, 0)
            self.SetCursor(wx.StockCursor(wx.CURSOR_BLANK))

    ## Methods Drawing on the IIDisplayFrame
    def draw_image_info(self, dc):
        #log('self.draw_image_info()')
        if self._image is None:
            #log('Ooops!')
            return
        info = ['Format: %s (%s)' % (self._image.image.format,
                                     self._image.mode_string()),
                '%d x %s Pixel' % (self._image.image.size),
                '%s Bytes' % self._image.filesize(),
                ] \
                + self._image.extra_info()
        # calculate position
        w, h = dc.GetSizeTuple()
        dc.SetFont(self.head_font)
        for i in range(4):
            head = break_url(self._image.url, i)
            tw = 0
            th = 0
            for s in head:
                hw, hh = dc.GetTextExtent(s)
                tw = max(tw, hw)
                th += hh
            if tw < 0.9*w:
                break
        #log(self._image.name, tw, th)
        dc.SetFont(self.info_font)
        for s in info:
            w, h = dc.GetTextExtent(s)
            #log(s, w, h)
            tw = max(tw, w)
            th += h
        w, h = dc.GetSizeTuple()
        #log('DC:', w, h)
        x = (w - tw) / 2
        y = int(h - 1.2 * th) / 2
        # draw heading and info strings
        dc.SetTextForeground(wx.Colour(self.foreground[0],
                                       self.foreground[1],
                                       self.foreground[2]))
        #log(self._image.name, x, y)
        #log(self.foreground)
        dc.SetFont(self.head_font)
        for s in head:
            #hw, hh = dc.GetTextExtent(s)
            dc.DrawText(s, x, y)
            y += int(1.2 * th / (len(info) +  + len(head)))
        dc.SetFont(self.info_font)
        for s in info:
            #log(s, x, y)
            dc.DrawText(s, x, y)
            y += int(1.2 * th / (len(info) + len(head)))

    def draw_image(self, dc):
        if self._bitmap is None:
            return
        dcw, dch = dc.GetSizeTuple()
        imw, imh = self._image.image.size
        dc.DrawBitmap(self._bitmap, (dcw - imw) / 2, (dch - imh) / 2)

    ## Event Handling Methods
    def handle_paint(self, event):
        #log('handle_paint(): state=%d' % (self.state))
        bg = apply(wx.Colour, self.background)
        dc = wx.PaintDC(self.panel)
        dc.SetBackgroundMode(wx.TRANSPARENT)
        dc.SetBackground(wx.TheBrushList.FindOrCreateBrush(bg))
        dc.Clear()
        if self.state == self.state_proc:
            nothing = None
        elif self.state == self.state_info:
            self.draw_image_info(dc)
        elif self.state == self.state_disp:
            self.draw_image(dc)
        ## DEBUG
        #if self.key:
        #    dc.SetFont(self.progress_font)
        #    dc.SetTextForeground(self.info_foreground)
        #    w, h = dc.GetSizeTuple()
        #    dc.DrawText('0x%02x' % self.key, 2*w/3, 4*h/5)
        #dc.DrawText('TEXT!', 10, 10)

    def handle_key(self, event):
        #log('handle_key() code: %x (=%d)'
        #    % (event.GetKeyCode(), event.GetKeyCode()))
        self.heartbeat()
        self.key = event.GetKeyCode()
        if self.key == 0x46:    # F
            #return
            self.toggle_fullscreen()
        elif self.key == 0x20 or self.key == 0x0d \
                or self.key == wx.WXK_NUMPAD2:
            # space or return: next image
            self.force_next_image()
            return
        elif self.key == 0x51:  # Q
            log('so long....')
            self.actions.flush()
            self.Close()
            return
        elif self.key == 0x4e:  # N
            return
        elif self.key == 0x43 or self.key == wx.WXK_NUMPAD1:
            # c: cached
            self.query_cache()
            return
        elif self.key == 0x44 or self.key == wx.WXK_NUMPAD4:
            # d: default
            self.query_default()
            return
        elif self.key == wx.WXK_NUMPAD3 or self.key == 0x59: # y
            self._special = (self._special + 1) % len(self.special_query_data)
            title, kwargs = self.special_query_data[self._special]
            self.query_google(title, **kwargs)
        elif self.key == 0x4c:
            # l: large
            self.query_google('Besonders große Grafiken',
                              size='xlarge|xlarge', start=0)
            return
        elif self.key == 0x53:
            # s: 
            self.query_google('Grafiken mit Schreibfehlern im Namen',
                              pattern='sapcer+balnk', start=0)
            return
        elif self.key == 0x47:
            # g: GIFs
            self.query_google('Nur GIFs', filetype='gif')
            return
        elif self.key == 0x50:
            # p: PNGs
            self.query_google('Nur PNGs', filetype='png')
            return
        elif self.key == 0x57:
            # w: w3.org
            self.query_google('w3.org', site='w3.org')
            return
        elif self.key == 0x41:
            # a: oestereich
            self.query_google('Invisible Austria! (Grafiken von österreichischen Websites)',
                              size='icon', site='at')
            return
#       elif self.key == 0x55:  # U
#           self.set_bg(self.display_background)
#           self._image = IImage('iu', 'ru', 'dots.gif')
#           self.set_state(self.state_disp)
#           self.display()
#           return
#       elif self.key == 0x49:  # I
#           self.set_bg(self.display_background)
#           self._image = IImage('iu', 'ru', 'dotst.gif')
#           self.set_state(self.state_disp)
#           self.display()
#           return
#       elif self.key == 0x4f:  # O
#           self.set_bg(self.display_background)
#           self._image = IImage('iu', 'ru', 'dots.png')
#           self.set_state(self.state_disp)
#           self.display()
#           return
#       elif self.key == 0x50:  # P
#           self.set_bg(self.display_background)
#           self._image = IImage('iu', 'ru', 'dotst.png')
#           self.set_state(self.state_disp)
#           self.display()
#           return
#       elif self.key == 0x58:  # X
#           self.state = self.state_info
#           self.set_fg(self.info_foreground)
#           self._image = IImage('iu', 'ru', 'test.png')
#           self.set_state(self.state_disp)
#           self.display()
#           return
#       elif self.key == 0x59:  # Y
#           log('testing actions...')
#           image = IImage('iu', 'ru', 'test.png')
#           self.show_image(image)
#           return
#       self.Refresh()


class IIMainFrame(wx.Frame):
    loglines=25
    foreground = wx.Colour(  0,   0,   0)
    background = wx.Colour(255, 255, 255)

    def __init__(self, parent=None, debug=False):
        wx.Frame.__init__(self, parent, -1,
                          name='The Invisible Image',
                          style=debug and wx.DEFAULT_FRAME_STYLE or wx.NO_BORDER)
        self.panel = wx.Panel(self)
        if parent and hasattr(parent, 'handle_key'):
            self.panel.Bind(wx.EVT_KEY_DOWN, parent.handle_key)

        x, y, w, h = wx.Display(0).GetGeometry()
        if debug:
            self.SetDimensions(x + w/2, y, w/2, h*2/3)
        else:
            self.SetDimensions(x, y, w, h)

        w, h = self.GetClientSizeTuple()
        from math import sqrt
        base_font_size = max(int(sqrt(w*w + h*h)) / 96, 10)

        # window elements
        title = wx.StaticText(self, style=wx.TE_CENTRE, size=(w, h/5),
                              label='the invisible image')
        title.SetFont(wx.Font(3*base_font_size,
                              wx.TELETYPE, wx.NORMAL, wx.BOLD))
        self.search = wx.StaticText(self, style=wx.TE_LEFT)
        self.search.SetFont(wx.Font(1.5*base_font_size,
                                    wx.TELETYPE, wx.NORMAL, wx.BOLD))
        self._buffer = []        # buffer for log text
        self._log = wx.StaticText(self, style=wx.TE_LEFT, size=(w, h/2))
        self._log.SetFont(wx.Font(base_font_size,
                                  wx.TELETYPE, wx.NORMAL, wx.NORMAL))

        # do layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(title, 0, wx.EXPAND | wx.ALL, 10)
        sizer.Add(self.search, 0, wx.EXPAND | wx.ALL, 10)
        sizer.AddSpacer(h/20)
        sizer.Add(self._log, 1, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(sizer)

    def set_query(self, name):
        log('Neue Suche: %s' % (name))
        self.search.SetLabel('Aktuelle Suche: %s' % (name))

    def log(self, str):
        self._buffer += str.split('\n')
        self._buffer = self._buffer[-self.loglines:]
        self._log.SetLabel('\n'.join(self._buffer))



class TheInvisibleImage(wx.App):
    def __init__(self, debug=False):
        self.debug = debug
        wx.App.__init__(self)

    def OnInit(self):
        if self.debug:
            log('Debugging set.')
        wx.InitAllImageHandlers()
        wx.SetDefaultPyEncoding('latin-1')
        globals()['the_cache'] = IICache()
        n = wx.Display.GetCount()
        log_debug('# displays: %d' % n)
        frame = IIDisplayFrame(display=wx.Display(n-1), debug=self.debug)
        main_frame = IIMainFrame(frame, debug=self.debug)
        frame.set_main_frame(main_frame)
        loggers.append(main_frame)

        self.SetTopWindow(frame)
        main_frame.Show(True)
        frame.Show(True)
        frame.Raise()

        if self.debug:
            frame.query_cache()
        else:
            frame.query_default()
        return True

##
## Main Program
##

log('Initialisiere...')
the_cache = None

#print the_cache.contents()

if __name__ == '__main__':
    try:
        app = TheInvisibleImage(debug = len(sys.argv) > 1
                                and sys.argv[1] == '-d')
        app.MainLoop()
    except:
        print 'Ooops!!!elf!'
        log('Ooops!!!elf!')
        log_debug(traceback.format_exc())
    if the_cache:
        the_cache.save()

## EOF
