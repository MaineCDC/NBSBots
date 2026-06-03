/*! $FileVersion=1.0.112 */
/*
 * COPYRIGHT (c) 2011 MCAFEE INC.  ALL RIGHTS RESERVED.
 */
var arrowheight = 16;
var arrowwidth = 15;
var borderheight = 245;
var borderwidth = 340;
var iconwidth = 16;
var iconheight = 16;
var hedge = 25;
var scrollbarwidth = 24;
var scrollbarheight = 16;
var g_path = "sacore:";
var baseUrlScriptElem = document.getElementById("saBaseUrl");
if (typeof baseUrlScriptElem != "undefined" && baseUrlScriptElem) {
  eval(baseUrlScriptElem.innerHTML);
  g_path = saBaseUrl;
}
document.onmousemove = MoveBubble;
if (document.all) {
  document.onmousewheel = BubbleHide;
} else {
  window.addEventListener("DOMMouseScroll", shut_ff, false);
}
var g_ct = 0;
var g_OkToMove = false;
var g_adjLeft = 0;
var g_adjTop = 0;
var g_adjZ = 0;
var g_color;
function pocpop(b, c, a) {
  return make_popup(b, c, a, false);
}
function pocpop_ss(b, c, a) {
  return make_popup(b, c, a, true);
}
function make_popup(uid, e, index, bSecureSearch) {
  g_UID = uid;
  var config;
  if (document.all) {
    config = eval(
      "(" +
        e.srcElement.parentNode.parentNode.getAttribute("mcBalloonConfig") +
        ")"
    );
  } else {
    config = eval(
      "( " +
        e.target.parentNode.parentNode.getAttribute("mcBalloonConfig") +
        ")"
    );
  }
  var annoItem;
  if (document.all) {
    annoItem = eval(
      "(" + e.srcElement.parentNode.parentNode.getAttribute("mcLinkinfo") + ")"
    );
  } else {
    annoItem = eval(
      "(" + e.target.parentNode.parentNode.getAttribute("mcLinkinfo") + ")"
    );
  }
  var linkTitleEncoded = annoItem.linkTitleEncoded;
  if (document.all) {
    g_path = config.resoureBaseUrl;
  }
  var facetList = PrepareLinks(config, annoItem);
  if (
    !document.all &&
    contains_ff(document.getElementById("BALLOON" + g_UID), e.relatedTarget)
  ) {
    return;
  }
  if (typeof annoItem.linkTitleEncoded == "undefined") {
    annoItem.linkTitleEncoded = annoItem.base_domain;
  }
  g_color = annoItem.color;
  g_adjLeft = annoItem.balloonConfig.adjustLeft;
  g_adjTop = annoItem.balloonConfig.adjustTop;
  g_adjZ = annoItem.balloonConfig.adjustZ;
  popup(annoItem, facetList, config, bSecureSearch);
  try {
    g_icon = document.all ? e.toElement : e.currentTarget;
  } catch (ex) {}
  g_ct = 0;
  g_OkToMove = true;
  if (document.all) {
    document.getElementById("BubbleLayer" + g_UID).onmouseout = shut_ie;
    document.getElementById("ArrowLayer" + g_UID).onmouseout = shut_ie;
  } else {
    document.getElementById("BubbleLayer" + g_UID).onmouseout = shut_ff;
    document.getElementById("ArrowLayer" + g_UID).onmouseout = shut_ff;
  }
  document.getElementById("BALLOON" + g_UID).style.width = "400px";
  MoveBubble(e);
}
function contains_ff(a, b) {
  while (b) {
    if (a == b) {
      return true;
    }
    b = b.parentNode;
  }
  return false;
}
function OffsetTop(b) {
  var a = b.offsetTop;
  while (b.offsetParent) {
    if (b.scrollTop) {
      a -= b.scrollTop;
    }
    b = b.offsetParent;
    a += b.offsetTop;
  }
  return a;
}
function OffsetLeft(b) {
  var a = b.offsetLeft;
  while (b.offsetParent) {
    b = b.offsetParent;
    if (b.className && b.className == "prel") {
      a += 10;
    } else {
      if (
        document.location.href.match(/uol\.com/) &&
        b.tagName &&
        b.tagName == "DT"
      ) {
        a += b.offsetLeft == 55 ? 10 : 0;
      } else {
        a += b.offsetLeft;
      }
    }
  }
  return a;
}
function MoveBubble(i) {
  if (g_OkToMove) {
    var c = g_color.charAt(0);
    if (document.all) {
      var h = document.documentElement.scrollLeft || document.body.scrollLeft;
      var k = document.documentElement.scrollTop || document.body.scrollTop;
      var j = document.documentElement.clientWidth || document.body.clientWidth;
      var a =
        document.documentElement.clientHeight || document.body.clientHeight;
    } else {
      var h = window.pageXOffset;
      var k = window.pageYOffset;
      var j = window.innerWidth;
      var a = window.innerHeight;
      var l = document.getElementById("arrow_bg_image");
    }
    var b = document.getElementById("ArrowLayer" + g_UID);
    var g = document.getElementById("BubbleLayer" + g_UID);
    b.style.width = arrowwidth + "px";
    b.style.height = arrowheight + "px";
    borderwidth = parseInt(
      document.getElementById("BALLOON" + g_UID).style.width
    );
    borderheight = document.getElementById("BALLOON" + g_UID).offsetHeight;
    g.style.width = borderwidth + "px";
    g.style.height = borderheight + "px";
    if (!document.all) {
      l.style.width = b.style.width;
      l.style.height = b.style.height;
    }
    var f = 0;
    var d = 0;
    if (g_icon.x && g_icon.y) {
      f = g_icon.x + g_adjLeft;
      d = g_icon.y + iconheight / 2;
    } else {
      f = OffsetLeft(g_icon) + g_adjLeft;
      d = OffsetTop(g_icon) + iconheight / 2;
    }
    if (f + scrollbarwidth + borderwidth > h + j) {
      if (document.all) {
        b.style.backgroundImage = "url(" + g_path + c + "rightarrow.gif)";
      } else {
        b.style.backgroundImage = "none";
        l.src = g_path + c + "rightarrow.gif";
      }
      b.style.top = d - arrowheight / 2 + "px";
      b.style.left = f - arrowwidth + 1 + "px";
      g.style.left = f - (borderwidth + arrowwidth - 1) + "px";
      g.style.top = d - borderheight / 2 + "px";
    } else {
      if (document.all) {
        b.style.backgroundImage = "url(" + g_path + c + "leftarrow.gif)";
      } else {
        b.style.backgroundImage = "none";
        l.src = g_path + c + "leftarrow.gif";
      }
      b.style.top = d - arrowheight / 2 + "px";
      b.style.left = f + iconwidth + "px";
      g.style.left = f + iconwidth + arrowwidth + "px";
      g.style.top = d - borderheight / 2 + "px";
    }
    b.style.backgroundRepeat = "no-repeat";
    if (d + (borderheight / 2 - hedge) > k + a - scrollbarheight) {
      g.style.top =
        Math.max(d - (borderheight - hedge), k + a - borderheight) + "px";
    } else {
      if (d < k + borderheight / 2) {
        g.style.top = Math.min(k, d - hedge) + "px";
      }
    }
    if (g_adjZ != 0) {
      g.style.zIndex = g_adjZ;
      b.style.zIndex = g_adjZ;
    }
    ShowBubble();
  }
}
function ShowBubble() {
  g_ct++;
  if (g_ct == 1) {
    document.getElementById("BubbleLayer" + g_UID).style.visibility = "visible";
    document.getElementById("ArrowLayer" + g_UID).style.visibility = "visible";
    g_OkToMove = false;
  }
}
function BubbleLayerHide(b) {
  var a = document.getElementById(b + g_UID);
  if (null != a) {
    a.style.visibility = "hidden";
    a.style.left = -800;
    a.style.top = -800;
  }
}
function BubbleHide() {
  if (!g_UID) {
    return;
  }
  BubbleLayerHide("BubbleLayer");
  BubbleLayerHide("ArrowLayer");
  if (document.all) {
    g_OkToMove = false;
  }
}
function shut_ie() {
  a = window.event;
  try {
    if (
      !document.getElementById("BubbleLayer" + g_UID).contains(a.toElement) &&
      !document.getElementById("ArrowLayer" + g_UID).contains(a.toElement) &&
      !g_icon.contains(a.toElement)
    ) {
      BubbleHide();
    }
  } catch (a) {}
}
function shut_ff(a) {
  try {
    if (
      !contains_ff(
        document.getElementById("BubbleLayer" + g_UID),
        a.relatedTarget
      ) &&
      !contains_ff(
        document.getElementById("ArrowLayer" + g_UID),
        a.relatedTarget
      ) &&
      typeof g_icon != "undefined" &&
      !contains_ff(g_icon, a.relatedTarget)
    ) {
      BubbleHide();
    }
  } catch (a) {}
}
if (!document.all) {
  MoveBubble();
}
var tooltip_js_common = document.createElement("script");
tooltip_js_common.src = g_path + "common.js";
document.getElementsByTagName("head")[0].appendChild(tooltip_js_common);
