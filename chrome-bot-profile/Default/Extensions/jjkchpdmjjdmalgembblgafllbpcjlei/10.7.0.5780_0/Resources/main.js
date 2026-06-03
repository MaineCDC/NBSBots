/*-----------------------------------------------------
  Copyright (c) 2009 McAfee, Inc.  All Rights Reserved.
  -----------------------------------------------------*/
var arrowheight=16;
var arrowwidth =15;
var borderheight= 245;
var borderwidth= 340;
var iconwidth=16;
var iconheight=16;
var hedge = 25; // edge of arrow to edge of bubble
var scrollbarwidth = 24;
var scrollbarheight = 6;
var g_UID;
var g_path = "sacore:";
var baseUrlScriptElem = document.getElementById("saBaseUrl");
if( typeof(baseUrlScriptElem) != 'undefined' && baseUrlScriptElem) {
	eval(baseUrlScriptElem.innerHTML);
	g_path = saBaseUrl;
}
//alert( g_path);
var g_color;

document.onmousemove = MoveBubble;
if (document.all)
	document.onmousewheel = BubbleHide;
else
	window.addEventListener("DOMMouseScroll",shut_ff, false);

var g_ct = 0;
var g_OkToMove = false;
var g_adjLeft = 0;
var g_adjTop = 0;
var g_adjZ = 0;


function trim(str, chars) {
	return ltrim(rtrim(str, chars), chars);
}
 
function ltrim(str, chars) {
	chars = chars || "\\s";
	return str.replace(new RegExp("^[" + chars + "]+", "g"), "");
}
 
function rtrim(str, chars) {
	chars = chars || "\\s";
	return str.replace(new RegExp("[" + chars + "]+$", "g"), "");
}

var FacetImages = 
    {
        "green":  g_path + "g_facet.gif",
        "yellow": g_path + "y_facet.gif",
        "red":    g_path + "r_facet.gif",
        "white":  g_path + "empty.gif"  
    };

var BannerBorder = 
    {
        "green":  "#54A411",
        "yellow": "#F0C649",
        "red":    "#FF5353",
        "white":  "#B9B9B9"  
    };

var DefaultBalloonImages = 
    {
        "green": 
        { backgroundImages:  
                { 
                "HEADER_L": "url("+g_path+"g_header_l.gif)", "HEADER_C": "url("+g_path+"g_header_c.gif)", "HEADER_R": "url("+g_path+"g_header_r.gif)", 
                "BANNER_L": "url("+g_path+"g_banner_l.gif)", "BANNER_C": "url("+g_path+"g_banner_c.gif)", "BANNER_R": "url("+g_path+"g_banner_r.gif)",
                "BANNER_BORDER_L": "url("+g_path+"g_bottom_l.gif)", "BANNER_BORDER_R": "url("+g_path+"g_bottom_r.gif)", 
                "BOTTOM_L": "url("+g_path+"g_bottom_l.gif)", "BOTTOM_C": "url("+g_path+"g_bottom_c.gif)", "BOTTOM_R": "url("+g_path+"g_bottom_r.gif)", //"BOTTOM_SEP": "url("+g_path+"g_bottom_sep.gif)",  
                "FOOTER_L": "url("+g_path+"g_footer_l.gif)", "FOOTER_C": "url("+g_path+"g_footer_c.gif)", "FOOTER_R": "url("+g_path+"g_footer_r.gif)"
                },
          srcImages:
                {
                "ICON": g_path+ "g_icon.gif", "BANNER_SEP": ""+g_path+"g_banner_sep.gif" //, "UPSELL_SEP": "+g_path+g_upsell_border.gif"
                }
        },
        "yellow": 
        { backgroundImages:  
                { 
                "HEADER_L": "url("+g_path+"y_header_l.gif)", "HEADER_C": "url("+g_path+"y_header_c.gif)", "HEADER_R": "url("+g_path+"y_header_r.gif)", 
                "BANNER_L": "url("+g_path+"y_banner_l.gif)", "BANNER_C": "url("+g_path+"y_banner_c.gif)", "BANNER_R": "url("+g_path+"y_banner_r.gif)",
                "BANNER_BORDER_L": "url("+g_path+"y_bottom_l.gif)", "BANNER_BORDER_R": "url("+g_path+"y_bottom_r.gif)", 
                "BOTTOM_L": "url("+g_path+"y_bottom_l.gif)", "BOTTOM_C": "url("+g_path+"y_bottom_c.gif)", "BOTTOM_R": "url("+g_path+"y_bottom_r.gif)", //"BOTTOM_SEP": "url("+g_path+"y_bottom_sep.gif)",
                "FOOTER_L": "url("+g_path+"y_footer_l.gif)", "FOOTER_C": "url("+g_path+"y_footer_c.gif)", "FOOTER_R": "url("+g_path+"y_footer_r.gif)"
                },
          srcImages:
                {
                "ICON": ""+g_path+"y_icon.gif", "BANNER_SEP": ""+g_path+"y_banner_sep.gif" //, "UPSELL_SEP": ""+g_path+"y_upsell_border.gif"
                }
        },
        "red": 
        { backgroundImages:  
                { 
                "HEADER_L": "url("+g_path+"r_header_l.gif)", "HEADER_C": "url("+g_path+"r_header_c.gif)", "HEADER_R": "url("+g_path+"r_header_r.gif)", 
                "BANNER_L": "url("+g_path+"r_banner_l.gif)", "BANNER_C": "url("+g_path+"r_banner_c.gif)", "BANNER_R": "url("+g_path+"r_banner_r.gif)",
                "BANNER_BORDER_L": "url("+g_path+"r_bottom_l.gif)", "BANNER_BORDER_R": "url("+g_path+"r_bottom_r.gif)", 
                "BOTTOM_L": "url("+g_path+"r_bottom_l.gif)", "BOTTOM_C": "url("+g_path+"r_bottom_c.gif)", "BOTTOM_R": "url("+g_path+"r_bottom_r.gif)", //"BOTTOM_SEP": "url("+g_path+"r_bottom_sep.gif)",
                "FOOTER_L": "url("+g_path+"r_footer_l.gif)", "FOOTER_C": "url("+g_path+"r_footer_c.gif)", "FOOTER_R": "url("+g_path+"r_footer_r.gif)"
                },
          srcImages:
                {
                "ICON": ""+g_path+"r_icon.gif", "BANNER_SEP": ""+g_path+"r_banner_sep.gif" //, "UPSELL_SEP": ""+g_path+"r_upsell_border.gif"
                }
        },
        "white": 
        { backgroundImages:  
                { 
                "HEADER_L": "url("+g_path+"w_header_l.gif)", "HEADER_C": "url("+g_path+"w_header_c.gif)", "HEADER_R": "url("+g_path+"w_header_r.gif)", 
                "BANNER_L": "url("+g_path+"w_banner_l.gif)", "BANNER_C": "url("+g_path+"w_banner_c.gif)", "BANNER_R": "url("+g_path+"w_banner_r.gif)",
                "BANNER_BORDER_L": "url("+g_path+"w_bottom_l.gif)", "BANNER_BORDER_R": "url("+g_path+"w_bottom_r.gif)", 
                "BOTTOM_L": "url("+g_path+"w_bottom_l.gif)", "BOTTOM_C": "url("+g_path+"w_bottom_c.gif)", "BOTTOM_R": "url("+g_path+"w_bottom_r.gif)", //"BOTTOM_SEP": "url("+g_path+"w_bottom_sep.gif)",
                "FOOTER_L": "url("+g_path+"w_footer_l.gif)", "FOOTER_C": "url("+g_path+"w_footer_c.gif)", "FOOTER_R": "url("+g_path+"w_footer_r.gif)"
                },
          srcImages:
                {
                "ICON": ""+g_path+"w_icon.gif", "BANNER_SEP": ""+g_path+"w_banner_sep.gif" //, "UPSELL_SEP": ""+g_path+"w_upsell_border.gif"
                }
        }
    };


function popup(e, annoItem, facetList, config, bSecureSearch) 
{
        var colour = annoItem.color; 
        var backgroundImages = DefaultBalloonImages[colour].backgroundImages;
        var siteReportLink = popUtil.getSiteReportLink(config, annoItem);

        for (var ID in backgroundImages)
        {
            try{
                    document.getElementById(ID + g_UID).style.backgroundImage=backgroundImages[ID]; 
            }
            catch(e) { 
            //alert(e.message); alert(ID); 
            }
        }
        
        var srcImages = DefaultBalloonImages[colour].srcImages;
        for (var ID in srcImages)
        {
            try{ 
                document.getElementById(ID + g_UID).src=srcImages[ID]; 
            }
            catch(e) { 
            //alert(e.message); 
            }
        }
        
        if (annoItem.hackerSafe && colour == "green")
        {
            document.getElementById("ICON" + g_UID).src = ""+g_path+"hs_icon.gif";
        }

	  if (typeof(config.IsPremium) != 'undefined')
		  document.getElementById("BALLOONLOGO" + g_UID).src = config.IsPremium ? ""+g_path+"sa-logo-plus.gif" : ""+g_path+"sa-logo.gif";
        
        document.getElementById("SATITLE" + g_UID).innerHTML = annoItem.linkTitleEncoded;
        document.getElementById("DOMAIN" + g_UID).innerHTML = annoItem.domain_specifier;
        var itemRec = document.getElementById("RECOMMENDATION" + g_UID);
	  itemRec.innerHTML = annoItem.recommendation;

	  itemRec.style.fontSize = "";
        itemRec.style.lineHeight = "";

        for (var nIndex = 0; nIndex < 3; nIndex++)
        {
            document.getElementById("FACET_IMAGE_" + nIndex + g_UID).innerHTML = "";
            document.getElementById("FACET_RECCOMENDATION_" + nIndex + g_UID).innerHTML = "";
        }

        for (var nIndex = 0; nIndex < facetList.length && nIndex < 3; nIndex++)
        {
            document.getElementById("FACET_IMAGE_" + nIndex + g_UID).innerHTML = facetList[nIndex].imageLink;
            document.getElementById("FACET_RECCOMENDATION_" + nIndex + g_UID).innerHTML = facetList[nIndex].recommendation[1];
        }
	  document.getElementById("BOTTOM_RIGHT" + g_UID).style.visibility = "";

	  for (var nIndex = 0; nIndex < 3; nIndex++)
	  {
           document.getElementById("CC_IMAGE_" + nIndex + g_UID).innerHTML = "";
           document.getElementById("CC_DESC_" + nIndex + g_UID).innerHTML = "";
	  }

        var CCList = annoItem.CCList;        
        if ( (typeof(CCList) != "undefined") && (CCList.length > 0) && (colour != "white"))
        {
            document.getElementById("CCHeader" + g_UID).innerHTML = config.CCHeader;
            document.getElementById("CCDesc" + g_UID).innerHTML = (typeof(config.CCLinkDesc_URL) != "undefined" ) ? config.CCDesc : "";
            document.getElementById("CCDesc" + g_UID).href = (typeof(config.CCLinkDesc_URL) != "undefined" && config.CCLinkDesc_URL != "" ) ? config.CCLinkDesc_URL : "http://www.siteadvisor.com/securesearch/";     
            
            for (var nIndex = 0; nIndex < CCList.length && nIndex < 3; nIndex++)
            {
			// de-dup functional group names
	          var nDup = 0;
		    for (; nDup < nIndex; nDup++) {
				if (CCList[nIndex]["desc"] == document.getElementById("CC_DESC_" + nDup + g_UID).innerHTML)
				     break;
		    }
		    if (nDup < nIndex)
			 break;
		    if (CCList[nIndex]["desc"].length > 0)
		    {
                	document.getElementById("CC_IMAGE_" + nIndex + g_UID).innerHTML = "<img src='"+g_path+"bullet.gif' />";
                	document.getElementById("CC_DESC_" + nIndex + g_UID).innerHTML = CCList[nIndex]["desc"];
		    }
            }
                    
            document.getElementById("BOTTOM_SEP" + g_UID).style.borderLeft = "solid 1px Gray";
	  }
	  else if ( (annoItem.balloonConfig.CCUpsell.length > 0) && (colour != "white") )
	  {
	      document.getElementById("CCHeader" + g_UID).innerHTML = "<span id='submitsitetxt' class='sastyle_link_upsell'>" + annoItem.balloonConfig.CCUpsell + "</span>";
          document.getElementById("BOTTOM_SEP" + g_UID).style.borderLeft = "solid 1px Gray";
          document.getElementById("CCDesc" + g_UID).innerHTML = "";
	  }
	  else
	  {  
   	      document.getElementById("CCHeader" + g_UID).innerHTML = (colour == "white") ? annoItem.link2 : "";
          document.getElementById("BOTTOM_SEP" + g_UID).style.borderLeft = "solid 0px #dadada";
          document.getElementById("CCDesc" + g_UID).innerHTML = "";
	  }

        if ( config.upsellInfo.display && typeof(config.upsellInfo.message) == 'string' && (trim(config.upsellInfo.message).length > 0)) 
        {
            document.getElementById("UPSELL_BORDER" + g_UID).style.borderBottom = "solid 1px #dadada";
            document.getElementById("UPSELL_LINK" + g_UID).innerHTML = trim(config.upsellInfo.message);
            document.getElementById("UPSELL_LINK" + g_UID).href = config.upsellInfo.url;
        }
        else
        {
            document.getElementById("UPSELL_BORDER" + g_UID).style.borderBottom = "solid 0px #dadada";
            document.getElementById("UPSELL_BORDER" + g_UID).style.borderLeft = "solid 0px #dadada";
            document.getElementById("UPSELL_LINK" + g_UID).innerHTML = "";
        }

     	document.getElementById("DOSSIER_LINK" + g_UID).innerHTML = config.siteReport.linkText;
     	document.getElementById("DOSSIER_LINK" + g_UID).href = annoItem.dossierUrl+"&ref=safesearch";

     	if (colour == "white" && document.getElementById("FACET_IMAGE_0" + g_UID).innerHTML == "")
     		document.getElementById("DOSSIER_LINK" + g_UID).innerHTML = "";

        document.getElementById("BANNER_ROW" + g_UID).style.borderColor = BannerBorder[colour];

        if (bSecureSearch && (typeof(config.HeaderText) == 'string') && (config.HeaderText != "") )
        {        
            document.getElementById("HEADER_C" + g_UID).innerHTML = config.HeaderText;
        }
        else
        {
            document.getElementById("HEADER_C" + g_UID).innerHTML = "&nbsp;";
        }
	
}

function contains_ff (container, containee) {
  while (containee) {
    if (container == containee) {
      return true;
    }
    containee = containee.parentNode;
  }
  return false;
}

function OffsetTop(elm) {
	if( typeof(elm.y) != 'undefined' ) return elm.y;
	var t = elm.offsetTop;
	while (elm.offsetParent) {
		if(elm.scrollTop){
			t-=elm.scrollTop;
		}
		elm = elm.offsetParent;
		t += elm.offsetTop;
	}
	return t;
}

function OffsetLeft(elm) {
	var l = elm.offsetLeft;
	while (elm.offsetParent) {
		elm = elm.offsetParent;
		if (elm.className && elm.className == "prel") l += 10;
		else if (document.location.href.match(/uol\.com/) && elm.tagName && elm.tagName == "DT") l += (elm.offsetLeft==55?10:0);
		else l += elm.offsetLeft;
	}
	return l;
}


function MoveBubble(e) {
	if(g_OkToMove) {
		var ch = g_color.charAt(0);
		if (document.all) {
			var pageXOffset = document.documentElement.scrollLeft || document.body.scrollLeft;
			var pageYOffset = document.documentElement.scrollTop || document.body.scrollTop;
			var innerWidth = document.documentElement.clientWidth || document.body.clientWidth;
			var innerHeight = document.documentElement.clientHeight || document.body.clientHeight;
		} else {
			var pageXOffset = window.pageXOffset;
			var pageYOffset = window.pageYOffset;
			var innerWidth = window.innerWidth;
			var innerHeight = window.innerHeight;
			var arrowimage = document.getElementById('arrow_bg_image');
		}

		var arrowlayer = document.getElementById('ArrowLayer' + g_UID);
		var bubblelayer = document.getElementById('BubbleLayer' + g_UID);

		arrowlayer.style.width = arrowwidth + "px";
		arrowlayer.style.height = arrowheight + "px";

		borderwidth = parseInt(document.getElementById('BALLOON' + g_UID).style.width);
		borderheight = document.getElementById('BALLOON' + g_UID).offsetHeight;

		bubblelayer.style.width = borderwidth + "px";
		bubblelayer.style.height = borderheight + "px";
		if (!document.all) {
			arrowimage.style.width = arrowlayer.style.width;
			arrowimage.style.height = arrowlayer.style.height;
		}
		
		var baseX = OffsetLeft(g_icon) + g_adjLeft; 	// left side of the icon
		var baseY = OffsetTop(g_icon) + iconheight/2; 	// middle of the icon

		// new way: box goes to the right of the icon (or the left if there's no room on right)
		if (baseX + scrollbarwidth + borderwidth > pageXOffset + innerWidth) {  // try left side
			if (document.all) {
 				arrowlayer.style.backgroundImage = "url(" + g_path + ch + "rightarrow.gif)";
			} else {
 				arrowlayer.style.backgroundImage = "none";
				arrowimage.src = g_path + ch + "rightarrow.gif";
			}
 			arrowlayer.style.top = (baseY - arrowheight/2) + "px";
			arrowlayer.style.left = (baseX - arrowwidth + 1) + "px";
			bubblelayer.style.left = (baseX - (borderwidth + arrowwidth - 1)) + "px";
			bubblelayer.style.top = (baseY - borderheight/2) + "px";
		} else {
		 	// Box is shown to the right of the target icon
			if (document.all) {
 				arrowlayer.style.backgroundImage = "url(" + g_path + ch + "leftarrow.gif)";
			} else {
 				arrowlayer.style.backgroundImage = "none";
				arrowimage.src = g_path + ch + "leftarrow.gif";
			}
 			arrowlayer.style.top = (baseY - arrowheight/2) + "px";
			arrowlayer.style.left = (baseX + iconwidth) + "px";
			bubblelayer.style.left = (baseX + iconwidth + arrowwidth) + "px";
			bubblelayer.style.top = (baseY - borderheight/2) + "px";
		}
		arrowlayer.style.backgroundRepeat = "no-repeat";
		// check for need to vertically slide the box to show as much as possible within the browser window
		if (baseY + (borderheight/2 - hedge) > pageYOffset + innerHeight - scrollbarheight) {
			bubblelayer.style.top = Math.max(baseY - (borderheight - hedge), (pageYOffset + scrollbarheight + innerHeight - borderheight)) + "px";
		} else if (baseY < pageYOffset + borderheight / 2) {
			bubblelayer.style.top = Math.min(pageYOffset, baseY - hedge) + "px";
		}
		
		if(g_adjZ != 0)
		{
			bubblelayer.style.zIndex = g_adjZ;
			arrowlayer.style.zIndex = g_adjZ;
		}
		
		ShowBubble();
	}
}

function ShowBubble() {
  	g_ct++;
	if(g_ct == 1) {
 		document.getElementById('BubbleLayer' + g_UID).style.visibility='visible';
		document.getElementById('ArrowLayer' + g_UID).style.visibility='visible';
		g_OkToMove = false;
  	}
}

function BubbleLayerHide(layername){
	var elem = document.getElementById(layername + g_UID);
	if (null != elem)
	{
		elem.style.visibility='hidden';
		elem.style.left=-800;
		elem.style.top=-800;
	}
}

function BubbleHide() {
	if (!g_UID) return;

	BubbleLayerHide('BubbleLayer');
	BubbleLayerHide('ArrowLayer');
	if (document.all) g_OkToMove = false;  // Fix a bug in IE, without this it's possible to move the mouse outside the popup and have it stay visible.
}

function shut_ie() {
	e = window.event;
    	try{
	    if (!document.getElementById('BubbleLayer' + g_UID).contains(e.toElement) && !document.getElementById('ArrowLayer' + g_UID).contains(e.toElement) && !g_icon.contains(e.toElement))
			BubbleHide();
        }
    	catch(e){
    	}
}

function shut_ff(e) {
    	try{
	    if ( !contains_ff(document.getElementById('BubbleLayer' + g_UID),e.relatedTarget) && !contains_ff(document.getElementById('ArrowLayer' + g_UID),e.relatedTarget) && typeof(g_icon) != "undefined" && !contains_ff(g_icon,e.relatedTarget))
		    BubbleHide();
	}
	catch(e){
	}
}
// 2 entry points:  pocpop (normal), pocpop_ss (SecureSearch logo)
function pocpop(uid, e, index)
{
	return make_popup(uid, e, index, false);
}
function pocpop_ss(uid, e, index)
{
	return make_popup(uid, e, index, true);
}

function make_popup(uid, e, index, bSecureSearch) {
    g_UID = uid;
    // get pageContent json response set during updatePageContextBalloonConfig
	var varName = "jsonRsp" + uid;
	var jsonRsp;
	//if the browser is google chrome, then we'll have the script tag.
	var scriptContent = document.getElementById( varName ).innerHTML;
	if( typeof( scriptContent) != 'undefined' && scriptContent ) {
		console.log( "script content : " + scriptContent );
		jsonRsp = eval( scriptContent );
	}
	jsonRsp = eval(varName);
  	var config = jsonRsp.config;
	var annoKey = jsonRsp.annotationList[index];
	var annoItem = jsonRsp.annotationMap[annoKey];

	var linkTitleEncoded = annoItem.linkTitleEncoded;
	if (document.all) g_path = config.resoureBaseUrl;
	var siteReportLink = popUtil.getSiteReportLink(config, annoItem);

	var upsellLink = popUtil.getUpsellLink(config);
   
	// populate: color, link1, link2
	popUtil.populateAnnoItem(config, annoItem, siteReportLink, upsellLink);
    
	// populate: top 3 three: imageLinks and recommendation
	var facetList = popUtil.populateFacets(config, annoItem);

	if (!document.all && contains_ff(document.getElementById('BALLOON' + g_UID), e.relatedTarget))
		return;

	if (typeof(annoItem.linkTitleEncoded) == 'undefined') 
		annoItem.linkTitleEncoded = annoItem.base_domain;

	g_color = annoItem.color;
	g_adjLeft = annoItem.balloonConfig.adjustLeft;
	g_adjTop = annoItem.balloonConfig.adjustTop;
	g_adjZ = annoItem.balloonConfig.adjustZ;

    	// call popup function to create the HTML for this balloon
	popup(e, annoItem, facetList, config, bSecureSearch);

	try {
	    g_icon = document.all ? e.toElement : e.currentTarget; // IE+FF
	}
	catch(ex){
	    //alert("Error (make_popup): " + ex);
	}

	g_ct = 0;
	g_OkToMove = true;

	if (document.all) {
		document.getElementById('BubbleLayer' + g_UID).onmouseout = shut_ie;
		document.getElementById('ArrowLayer' + g_UID).onmouseout = shut_ie;
	} else {
		document.getElementById('BubbleLayer' + g_UID).onmouseout = shut_ff;
		document.getElementById('ArrowLayer' + g_UID).onmouseout = shut_ff;
	}
	MoveBubble(e);

}

var FacetList  = ["rogue", "download", "personal_info", "ecommerce", "link", "annoyance"]
var TypePriority  = {"rogue": 0, "download": 1, "personal_info": 2, "ecommerce": 3, "link": 4, "annoyance": 5}
var ScorePriority = {"WARN": 0, "INFO": 1, "OK": 2, "CERTIFIED": 3, "UNKNOWN": 4}

function FacetTypePrioritySort(a, b)
{

  var aPriority = TypePriority[a.name];
  var bPriority = TypePriority[b.name];
  if (aPriority < bPriority)
     return -1;
  if (aPriority > bPriority)
     return 1;
  return 0;
}

function FacetPrioritySort(a, b)
{
  var aPriority = ScorePriority[a.score];
  var bPriority = ScorePriority[b.score];
 
  if (aPriority < bPriority)
     return -1;
  if (aPriority > bPriority)
     return 1;
  return FacetTypePrioritySort(a, b);
}

function PopUtil(){}
var popUtil = new PopUtil();

PopUtil.prototype.getSiteReportLink = function getSiteReportLink(config, annoItem)
{
    var hrefurl = config.siteReport.siteReportBaseUrl + annoItem.domain_specifier + "?" + config.siteReport.requestArgs;
    return "<a class='sastyle_link_moreinfo' style='white-space:nowrap;color:#012D6F;padding-right:10px;font-weight:normal' href='" 
        + hrefurl + "' target=_blank>" + config.siteReport.linkText + "</a>";					

}
PopUtil.prototype.getSubmitForTestingLink = function getSubmitForTestingLink(config)
{
	
	return "<a style='text-decoration:none' href='#' onclick='return false;'><img id='submitsiteimg' border='0' style='display:inline;margin-bottom:12px;width:16px;font-size:medium;' src='" 
		//+ config.resoureBaseUrl 
		//Changed for google chrome. Use the g_path here.
		+ g_path
		+ "protection.gif'/>&nbsp;<span id='submitsitetxt' class='sastyle_link_submittest' style='vertical-align:top;text-decoration:none;color:black;white-space:nowrap;line-height:normal;'>" 
		+ config.unratedSubmitText 
		+ "&nbsp;</span></a>";
}
PopUtil.prototype.displayUpsell = function displayUpsell(config)
{
    if ( config.upsellInfo.display && typeof(config.upsellInfo.message) == 'string') {
        if ( trim(config.upsellInfo.message).length > 0) {
           	return true;
        }
    }
    return false;
}
PopUtil.prototype.getUpsellLink = function getUpsellLink(config)
{
    var upsellLink = "<td style='font-family:sans-serif;font-size:8px;line-height:100%'>&nbsp;</td>";
    if (this.displayUpsell(config))
    {
		upsellLink = 
			"<td colspan=2 align=center><table border='0' cellspacing='0' cellpadding='0' style='table-layout:auto;margin-bottom:10px;margin-left:11px;'><tr>"
			+ "<td style='width:2px;height:24px;background:url("+g_path+"upsell-l.gif) 0 0 no-repeat;'></td>"
			+ "<td class='sastyle_link_upsell' style='cursor:default;height:24px;background:url(" + g_path + 
				"upsell-m.gif) 0 0 repeat-x;text-decoration:none;white-space:nowrap;color:black;line-height:normal;'>"
			+ "<a class='sastyle_link_upsell' style='padding:0 10px;text-decoration:none;font-weight:normal' target='_blank' href='" + config.upsellInfo.url + "'>"
			+ config.upsellInfo.message + "</a></td><td style='width:2px;height:24px;background:url("+g_path+"upsell-r.gif) 0 0 no-repeat;'></td> </tr></table></td>";
    }
    return upsellLink;
}

var ScoreToColor  = {"OK":"green", "CERTIFIED":"green", "INFO":"yellow", "WARN":"red", "UNKNOWN":"white", "":"white"}

PopUtil.prototype.getFacetImage = function getFacetImage(imageSrc)
{
   // var iconheight = ".7512em";
    var iconheight = "18px";
    return "<img style='font-size:medium;height:" + iconheight + ";' border=0 src='" + imageSrc + "'></a>"; 
}

PopUtil.prototype.populateAnnoItem = function populateAnnoItem(config, annoItem, siteReportLink, upsellLink)
{
      annoItem.color = ScoreToColor[annoItem.score];
	if (annoItem.color == "white") {		  
            annoItem.link1 = "";
            annoItem.link2 = "";//this.getSubmitForTestingLink(config);
	} else {
      	annoItem.link1 = siteReportLink;
      	annoItem.link2 = upsellLink;
	}
}

var FacetToPageName = {"download":"downloads", "annoyance":"annoyances", "link":"links", "personal_info":"email", "ecommerce":"ecommerce", "rogue":"rogue", "":""}

PopUtil.prototype.populateFacets = function populateFacets(config, annoItem)
{
    var dssUrlInfo = config.siteReport;
    var facetInfo, imageName, imageTag, url;
    var facetList = [];
    
    if (typeof(annoItem.facets) != 'object'){
    	// some responses have no facet map
    	annoItem.facets = {};
    }

    for (var facet in annoItem.facets)
    {
        annoItem.facets[facet].name = facet // we will need this info during sorting
        if (annoItem.facets[facet].score == "UNKNOWN"){
            // unknown facets are not displayed in facet slots
        }
        else{
            facetList.push(annoItem.facets[facet]);
        }
    }
     
    // Sort by Score, FacetType
    facetList.sort(FacetPrioritySort);
    
    // push facet information into Rated and Unrated lists
    for (var fi in facetList)
    {	
        var facetInfo = facetList[fi];
        imageName = FacetImages[ScoreToColor[facetInfo.score]];
        imageTag = this.getFacetImage(imageName);
        url = dssUrlInfo.siteReportBaseUrl + annoItem.domain_specifier + "/" + FacetToPageName[facetInfo.name] + "?" + dssUrlInfo.requestArgs+"&ref=safesearch";
        facetInfo.imageLink = "<a href='" + url + "' target='_blank'>" + imageTag + "</a>";      
    }
    return facetList;
}

if (!document.all) {
	MoveBubble(); 
}
