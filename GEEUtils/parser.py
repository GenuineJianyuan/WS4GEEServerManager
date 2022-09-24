from numpy import empty
from GEEUtils import gee_utils
from xml.dom.minidom import parseString
from Utils import general_utils
from WS4GEEServerManager.settings import BASE_DIR
import os


def getServiceName(xmlDoc,serviceType):
    return

def retrieve_attr(rawData,method):
    dom = parseString(rawData) 
    root = dom.documentElement
    rootName=root.nodeName
    if method=="GetCoverage":
        if (rootName!="GetCoverage"):
            return "{'error':'Please check the XML document'}"
        identifier=root.getElementsByTagName('ows:Identifier')[0].firstChild.data
        lowerCorner=root.getElementsByTagName('ows:LowerCorner')[0].firstChild.data.split(" ")
        upperCorner=root.getElementsByTagName('ows:UpperCorner')[0].firstChild.data.split(" ")
        crs=root.getElementsByTagName('ows:BoundingBox')[0].getAttribute("crs") 
        return {'identifier':identifier,'lowerCorner':lowerCorner,'upperCorner':upperCorner,'crs':crs}
    elif method=="Execute":
        if (rootName!="wps:Execute"):
            return "{'error':'Please check the XML document'}"
        identifier=root.getElementsByTagName('ows:Identifier')[0].firstChild.data
        inputs=root.getElementsByTagName('wps:Input')
        variables=[]
        # use identifier as unique index, read all inputs/outputs as dictionaries
        for input in inputs:
            curInputParam={}
            curInputParam["identifier"]=input.getElementsByTagName('ows:Identifier')[0].firstChild.data
            if len(input.getElementsByTagName('wps:Reference')) !=0:
                ## Currently just accept wps:Reference and href
                curInputParam["value"]=input.getElementsByTagName('wps:Reference')[0].getAttribute("xlink:href")
                curInputParam["mimeType"]=input.getElementsByTagName('wps:Reference')[0].getAttribute("mimeType")
            if len(input.getElementsByTagName('wps:LiteralData')) !=0:
                curInputParam["value"]=input.getElementsByTagName('wps:LiteralData')[0].firstChild.data
            variables.append(curInputParam)

        #currently accept wps:ResponseForm, storeExecuteResponse="true", asReference="true"
        outputs=root.getElementsByTagName('wps:ResponseDocument') 
        if (outputs is empty) | (len(outputs)==0):
            return {'error':'Only wps:ResponseDocument is currently supported for the output'}
        if (outputs[0].getAttribute("storeExecuteResponse")!='true'):                      # Only one ResponseDocument exists
            return {'error':'Only storeExecuteResponse=\"true\" is currently supported for the output'}

        for output in outputs[0].getElementsByTagName('wps:Output'):
            if (output.getAttribute("asReference")!='true'):
                return {'error':'Only asReference=\"true\" is currently supported for the output'}
            curOutputParam={}
            curOutputParam["mimeType"]=output.getAttribute("mimeType")
            curOutputParam["identifier"]=output.getElementsByTagName('ows:Identifier')[0].firstChild.data
            variables.append(curOutputParam)

        # outputs=root.getElementsByTagName('wps:RawDataOutput')
        # for output in outputs:
        #     curOutputParam={}
        #     curOutputParam["mimeType"]=output.getAttribute("mimeType")
        #     curOutputParam["identifier"]=output.getElementsByTagName('ows:Identifier')[0].firstChild.data
        #     variables.append(curOutputParam)
        
    params={"identifier":identifier,"variables":variables}
    return params

def convert_to_ee_vector(content,type="geojson"):
    if (type=='geojson'):
        return gee_utils.generateEEFeaturesFromJSON(content)

def convert_to_ee_image():
    return

def convert_by_ee_cloud(url,type="tiff"):
    if (type=='tiff'):
        fileName=general_utils.getuuid12()+".tif"
        savePath=os.path.join(BASE_DIR,'temp')
        saveAbsPath=os.path.join(savePath,fileName)
        general_utils.readFileFromUrl(url,fileName,savePath)
        eeCloudPath=gee_utils.upload_blob("image_bucket_leismars",saveAbsPath,fileName)
        return gee_utils.generateEERasterFromCloud(eeCloudPath)
    return

def convert_by_ee_cloud_test(url,type="tiff"):
    if (type=='tiff'):
        fileName=general_utils.getuuid12()+".tif"
        savePath=os.path.join(BASE_DIR,'temp')
        saveAbsPath=os.path.join(savePath,fileName)
        general_utils.readFileFromUrl(url,fileName,savePath)
        eeCloudPath=gee_utils.upload_blob("image_bucket_leismars",saveAbsPath,fileName)
        print(eeCloudPath)
        return gee_utils.generateEERasterFromCloudTest(eeCloudPath)
    return
