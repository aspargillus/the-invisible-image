README
==

The Invisible Image was an installation displaying spacer GIFs found on the web.

History
--

The original idea for this project was muttered by Christopher Clay
and the first incarnation of the installation was on display for the
[first Paraflows Festival](http://2006.paraflows.at/) in September
2006 at [the metalab](http://metalab.at) in Vienna.

The second incarnation was (much refined) shown at the
[Museumsquartier](http://www.mqw.at/) in Vienna in 2007. This is
basically the version you can find here.


What are Spacer GIFs?
--

Spacer GIFs, also called blind GIFs though they may as well be of
other graphics formats, are an anachronism from the early days of the
world wide web: back in the early to mid 1990s, before the advent of
cascading style sheets (CSS), means for specifying the layout of a web
site - especially ensuring the exact positioning of page
elements - were quite limited. And one of them were spacer GIFs.
Their purpose was to help position other elements of the page by
keeping portions of that page empty, e.g. separating entries of a
navigation menu or text columns in a multi-column layout.

Technically, though, these apparently empty spaces are not empty at
all. They are occupied by images which just happen to be invisible, a
whole species unnoticed by unsuspecting visitors of the sites they
dwell on.

Another remarkable propertiy of spacer GIFs is that they constitute a
Hack in the classical sense of the word: they are a very clever
(ab?)use (generating empty space in a page) of a means (embedding
images in a text document) invented for an entirely different purpose
(providing illustrations and figures).

They also are a species endangered by extinction: todays means of
specifying page layout are vastly superior, thus, rendering spacer
GIFs obsolete. This installation is dedicated to these normally unseen
images, dragging them out of their niches and hideaways before they
die out completely. So this may be your Last Chance (not) To See.


How it works
--

At the core of the installation is a python program that searches the
web for spacers using Google Images (by screen scraping - there was no
image API back then). More precisely, it searches for images with
names that likely will return many spacer GIFs. It then downloads the
images and tests them for transparency. If it finds them to be
entirely invisible, it will display them.


What you see (or don't)
--

While it searches for more invisible images, the program shows its
progress. Once a spacer GIF has been found you are shown the images
meta-data, i.e. its URL, dimensions in pixels, size in Bytes etc. It
then switches to display the image itself. In parallel, the layout
structure of a page, which references the image, in is also shown in a
browser. Page elements are only shown as gray blocks. The deeper
nested the element, the brighter it is shown. The spacer GIF itself is
appearing in red. This magic is acieved by a
[Greasemonkey](https://addons.mozilla.org/en-US/firefox/addon/greasemonkey/)
script contributed by [Christopher Clay](https://twitter.com/c3o).

Setting it up yourself
--

In it's current shape, the installation is geared to be run on a Mac.


Most likely this will

In any case, you'll need this:

* Python
* wxWidgets with python bindings (for the display / UI)
* Beautifulsoup (for screen scraping)
* Appscript (for making a Firefox process display the page, [seems defunct](http://appscript.sourceforge.net/status.html) as of Mac OS 10.8)
* In case you want to run it like the original: a beamer.

Assuming you are using [macports](http://macports.org/), do the following:

* `sudo port install python27 wxWidgets30 py27-wxpython30 py27-beautifulsoup py27-appscript`
* Install the [Greasemonkey](https://addons.mozilla.org/en-US/firefox/addon/greasemonkey/) Firefox addon and add add `invisible-image-greasemonkey.js` to you user scripts, activated for all URLs.
* run `python2.7 ii.py -d` for testing and debugging and `python2.7 ii.py` fot the full two-screen setup.
