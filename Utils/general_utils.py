import os
import uuid,json
from xml.dom.minidom import Document
import requests



def getuuid12():
    str1=str(uuid.uuid4())
    str1=str1[str1.rindex( '-' ) + 1 : len( str1 ) ]
    return str1

def getuuid():
    return str(uuid.uuid4())

def lastDayInMonth(year,month):
        if month in [1,3,5,7,8,10,12]:
            return 31
        elif month in [4,6,9,11]:
            return 30
        else:
            if year % 4==0:
                return 29
            else:
                return 28

def split_time_by_month(start,end):
    fmt_list =start.split("-")
    start_year,start_month,start_day=fmt_list[0],fmt_list[1],fmt_list[2]
    fmt_list2 =end.split("-")
    end_year,end_month,end_day=fmt_list2[0],fmt_list2[1],fmt_list2[2]
    periods=[]
    cur_year,cur_month,cur_day=start_year,start_month,start_day
    while (int(cur_year)<int(end_year)) or ((int(cur_year)==int(end_year)) and (int(cur_month)<=int(end_month))):
        period={}
        cur_lastday=-1
        period["start_year"],period["start_month"],period["start_day"]=cur_year,cur_month,cur_day
        if (cur_year==end_year) and (cur_month==end_month):
            cur_lastday=end_day
        else:
            cur_lastday=str(lastDayInMonth(int(cur_year),int(cur_month)))
        period["end_year"],period["end_month"],period["end_day"]=cur_year,cur_month,cur_lastday
        periods.append(period)
        
        if cur_month==str(12):
            cur_day='01'
            cur_month='01' #next month
            cur_year=str(int(cur_year)+1)
        else:
            cur_day='01'
            cur_month=str(int(cur_month)+1) #next month
            if int(cur_month)<10:
               cur_month='0'+cur_month

    # get total months
    return periods

def split_time_by_year(start,end):
    fmt_list =start.split("-")
    start_year,start_month,start_day=fmt_list[0],fmt_list[1],fmt_list[2]
    fmt_list2 =end.split("-")
    end_year,end_month,end_day=fmt_list2[0],fmt_list2[1],fmt_list2[2]
    periods=[]
    cur_year=start_year
    while (int(cur_year)<=int(end_year)):
        period={}
        if (cur_year==start_year):
            period["start_year"],period["start_month"],period["start_day"]=start_year,start_month,start_day
            period["end_year"],period["end_month"],period["end_day"]=cur_year,'12','31'
        elif (cur_year<end_year):
            period["start_year"],period["start_month"],period["start_day"]=cur_year,'01','01'
            period["end_year"],period["end_month"],period["end_day"]=cur_year,'12','31'
        elif (cur_year==end_year):
            period["start_year"],period["start_month"],period["start_day"]=end_year,'01','01'
            period["end_year"],period["end_month"],period["end_day"]=end_year,end_month,end_day
        cur_year=str(int(cur_year)+1)
        periods.append(period)
    return periods

def split_time_by_custom(start,end):
    fmt_list =start.split("-")
    start_year,start_month,start_day=fmt_list[0],fmt_list[1],fmt_list[2]
    fmt_list2 =end.split("-")
    end_year,end_month,end_day=fmt_list2[0],fmt_list2[1],fmt_list2[2]
    periods=[
        {"start_year":start_year,"start_month":start_month,"start_day":start_day,
        "end_year":end_year,"end_month":end_month,"end_day":end_day}
    ]
    return periods


def readLocalFileToStr(file_path):
    if not os.path.isfile(file_path):
        raise TypeError(file_path + " does not exist")

    all_the_text = open(file_path,encoding='utf-8').read()
    # print type(all_the_text)
    return all_the_text

def matchDatasetName(org_name):
    if org_name=='Landsat 8 Surface Reflectance Tier 1':
        return 'Landsat_SR_T1'
    else:
        return org_name

def matchDatasetSnippetName(org_name):
    if org_name=='Landsat 8 Surface Reflectance Tier 1':
        return 'LANDSAT/LC08/C01/T1_SR'
    else:
        return org_name

def getBoundary(geojsonData):
    geojson=json.loads(geojsonData)
    features=None
    minX,maxX,minY,maxY=9999,-1,9999,-1
    if geojson["type"] == "FeatureCollection":
        # need WGS84 Coordinate
        if (geojson["crs"]['properties']['name']!='EPSG:4326'):
            return [-1,-1,-1,-1]
        features=geojson["features"]
        for feature in features:
            if (feature["geometry"]["type"]=='Polygon'):
                for level1XYs in feature["geometry"]["coordinates"]:
                    for pair in level1XYs:
                        curX,curY=pair[0],pair[1]
                        if (curX>maxX):
                            maxX=curX
                        if (curY>maxY):
                            maxY=curY
                        if (curX<minX):
                            minX=curX
                        if (curY<minY):
                            minY=curY
    return [minX,minY,maxX,maxY]

def setText(node,content):
    doc = Document() 
    node.appendChild(doc.createTextNode(content))
    return node

def setTexts(node,childElementName,contentList):
    doc = Document() 
    for content in contentList:
        node.appendChild(setText(doc.createElement(childElementName),content))
    return node

def setElements(node,elements):
    for element in elements:
        node.appendChild(element)
    return node

def setAttributes(node,attributes):
    for key in attributes.keys():
        node.setAttribute(key,attributes[key])
    return node

def getXMLStrfromMinidom(dom):
    import sys
    class XmlStdin():
        def __init__(self):
            self.str=""

        def write(self,value):
            self.str+=value
    
        def toString(self):
            return self.str

    xmlStdin=XmlStdin()
    sys.stdin=xmlStdin
    dom.writexml(sys.stdin, addindent='\t', newl='\n', encoding='utf-8')
    return xmlStdin.toString()

def readStrFromUrl(url):
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows; U; Windows NT 5.2) Gecko/2008070208 Firefox/3.0.1"
    }
    content= requests.get(url,headers=headers,proxies={"http":None,"https":None})
    return content.text

def readFileFromUrl(url,filename,savePath):
    curFile=requests.get(url)
    finalPath=os.path.join(savePath,filename)
    open(finalPath,'wb').write(curFile.content)