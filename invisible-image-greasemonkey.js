// ==UserScript==
// @name          Invisible Image
// @namespace     http://c3o.org/code/greasemonkey
// @description	  Shows specified image
// @include       *
// ==/UserScript==

if(document.location.search.indexOf('hiliteimg=') > -1) {
  var dls = document.location.search;
  var snip = dls.substring(dls.indexOf('hiliteimg=')+10);
  var s = snip.substring(0, snip.indexOf('&'));
  if(s != '') { doChildren(document.body, s, 0); }
  document.body.style.background = '#000';
}

function doChildren(o, s, e) {
  var c = o.childNodes;
  for (var i=0; i<c.length; i++) {
    if(c[i] && c[i].style) {
      var val = 10*e;
      //c[i].style.opacity = '.1';
      //var val = Math.round(i/(c.length/255));
      c[i].style.background = 'rgb('+val+', '+val+', '+val+')';
      c[i].style.color = 'rgb('+val+', '+val+', '+val+')';
      c[i].style.border = '0';
      if(c[i].tagName == 'IMG') {
        if(c[i].src == s) {
          c[i].style.backgroundColor = 'red';
          var current = c[i];
          var yoff = 0;
          while(current.tagName != 'BODY') {
            yoff += current.offsetTop;
            current = current.offsetParent;
          }
          window.scroll(0,
                        yoff - (window.innerHeight - c[i].offsetHeight) / 2);
        }
        var ow = c[i].offsetWidth;
        var oh = c[i].offsetHeight;
        c[i].src = 'data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==';
        c[i].style.width = ow+'px';
        c[i].style.height = oh+'px';
      }
    }
    if(c[i].tagName == 'A') {
	c[i].href = '#'
    }
    if(c[i].hasChildNodes) {
      doChildren(c[i], s, e+1);
    }
  }
}
