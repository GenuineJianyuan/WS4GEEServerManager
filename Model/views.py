
from email.policy import default

# from urllib.error import HTTPError
# from django.core.checks.messages import Error

from django.http import HttpResponse
import sys
import os
from Utils import general_utils
from GEEUtils import gee_utils, generator, parser
from Model.models import SearchRequest, DynamicWcs, DownloadingLog, Process, ProcessParams, ParamRecord, ParamRequest, ExecuteStatusRecord
import threading
import json

from WS4GEEServerManager.settings import BASE_DIR,PROJECT_ROOT_URL,File_ACCESS_PATH

def test(request):
    url="http://43.154.247.161:8080/examples/temp/test.tif"
    result=parser.convert_by_ee_cloud_test(url, "tiff")
    return HttpResponse(result)

def set_group_name(request):
    oldName=request.POST.get('groupName',0)
    newName=request.POST.get('newGroupName',0)
    SearchRequest.objects.filter(generate_name=oldName).update(generate_name=newName)
    responseDir = {}
    responseDir['code'] = 0
    return HttpResponse(str(responseDir))

def get_files(request):
    if request.method == 'POST':
        if request.FILES:
            myFile = None
            for i in request.FILES:
                myFile = request.FILES[i]
            if myFile:
                dir = os.path.join(BASE_DIR, 'GEEScriptTemplates')
                destination = open(os.path.join(dir, myFile.name),
                                   'wb+')
                for chunk in myFile.chunks():
                    destination.write(chunk)
                destination.close()
            return HttpResponse('ok')

def get_boundary_files(request):
    if request.method == 'POST':
        if request.FILES:
            myFile = None
            for i in request.FILES:
                myFile = request.FILES[i]
            if myFile:
                dir = os.path.join(BASE_DIR, 'static')
                destination = open(os.path.join(dir, myFile.name),
                                   'wb+')
                for chunk in myFile.chunks():
                    destination.write(chunk)
                destination.close()
            return HttpResponse('ok')

def get_xmlTemplate_list(request):
    xmlList=["GetCapabilities.xml","DescribeProcess.xml","test_buffer.xml","test_FVC.xml","test_raster_add.xml"]
    responseDir = {}
    responseDir['code'] = 0
    responseDir['data'] = xmlList
    return HttpResponse(str(responseDir))

def get_xmlTemplate(request):
    import time
    curId = request.GET.get("curId")
    docStr = general_utils.readLocalFileToStr(
        os.path.join(BASE_DIR, 'static/testing template',curId))
    return HttpResponse(docStr, "text/xml")

def register_wps(request):
    responseDir = {}
    responseDir['code'] = 0
    responseDir['data'] = ''
    scriptPath = request.POST.get('scriptPath', 0)
    entranceFunc = request.POST.get('entranceFunc', 0)
    entranceName = request.POST.get('entranceName', 0)
    processName = request.POST.get('processName', 0)
    processAbstract = request.POST.get('processAbstract', 0)
    processTitle = request.POST.get('processTitle', 0)
    checked = request.POST.get('checked', 0)

    inputForm = request.POST.get('inputForm', 0)
    outputForm = request.POST.get('outputForm', 0)
    defaultForm = request.POST.get('defaultForm', 0)
    inputForm, outputForm, defaultForm = eval(json.loads(json.dumps(inputForm))), eval(
        json.loads(json.dumps(outputForm))), eval(json.loads(json.dumps(defaultForm)))
    processUuid=uuid=general_utils.getuuid12()
    curProcess = Process(processUuid, name=processName, entrance_func=entranceFunc,
                         script_path=scriptPath, title=processTitle, abstract=processAbstract, entrance_name=entranceName)
    curProcess.save()
    count = 1
    if (checked == 'true'):
        for item in defaultForm:
            curParam = ProcessParams(uuid=general_utils.getuuid12(), param_name=item['name'], data_type=item['type'], order=count, param_type='input',
                                     process_uuid=processUuid,title=item['title'],min_occurs=int(item['minOccurs']),max_occurs=int(item['maxOccurs']),value_type=1)
            curParam.save()
            count=count+1
    for item in inputForm:
        literalValuesSetting=None
        if (item['literalValuesChoice']=='1'):
            literalValuesSetting=item['literalValuesSetting']
        curParam = ProcessParams(uuid=general_utils.getuuid12(), param_name=item['name'], data_type=item['type'], order=count, param_type='input',
                                     process_uuid=processUuid,title=item['title'],min_occurs=int(item['minOccurs']),max_occurs=int(item['maxOccurs']),
                                     abstract=item['abstract'],value_type=int(item['literalValuesChoice']),default_value=item['defaultValue'],allowed_value=literalValuesSetting)
        count=count+1
        curParam.save()
    for item in outputForm:
        curParam = ProcessParams(uuid=general_utils.getuuid12(), param_name=item['name'], data_type=item['type'], order=count, param_type='output',
                                     process_uuid=processUuid,title=item['title'],value_type=1)
        count=count+1
        curParam.save()
    return HttpResponse(str(responseDir))


# For WCS service generation, the parameters are record in DB, with constraints the creator sets
# The settings are in the DescribeCoverage operations and shown in the <abstract> label
def generate_dynamic_service(request):
    serviceType = request.POST.get('serviceType', 0)
    datasetName = 'Landsat 8 Surface Reflectance Tier 1'
    # request.POST.get('datasetName', 0)
    stackingMethod = request.POST.get('stackingMethod', 0)
    start = request.POST.get('start', 0)
    end = request.POST.get('end', 0)
    options=str(request.POST.get('options', 0)).split(',')
    dataAbstract = request.POST.get('dataAbstract', 0)
    keywords = request.POST.get('keywords', 0)
    uploadType = request.POST.get('uploadType', 0)
    uploadBoundaryName=request.POST.get('uploadBoundaryName', 0)
    uploadBoundaryContent = request.POST.get('uploadBoundaryContent', 0)
    bandsName = request.POST.get('bands', 0) # e.g. B1;B2;B3
    
    noCloud,byYear,byMonth,byCustom = 0,0,0,0

    boundary,boundaryName='',uploadBoundaryName
    if ('noCloud' in options):
        noCloud=1
    if ('byMonth' in options):
        byMonth=1
    if ('byYear' in options):
        byYear=1
    if ('byCustom' in options):
        byCustom=1
    if (int(uploadType)==2):
        boundary=general_utils.readStrFromUrl(uploadBoundaryContent)
    else:
        boundary=general_utils.readLocalFileToStr(os.path.join(BASE_DIR, 'static',uploadBoundaryContent))

    bands=str(bandsName).split(';') 
    keywords=str(keywords).split(';')
    print(dataAbstract)
    # datasetInfo=""
    datasetInfo = gee_utils.getTargetDatasetInfo(
        general_utils.matchDatasetSnippetName(datasetName), start, end, boundary)
    envelope=gee_utils.getBoundaryBox(boundary)
    # Store data
    requestUuid = general_utils.getuuid12()
    generate_name=boundaryName+requestUuid
    newSearchRequest = SearchRequest(uuid=requestUuid, dataset_name=datasetName, service_type=serviceType,
                                     stacking_method=stackingMethod, start=start, end=end, boundary=boundary,
                                     boundary_name=boundaryName, abstract=dataAbstract,keywords=keywords,no_cloud=int(noCloud), by_year=int(byYear), 
                                     by_month=int(byMonth), dataset_info=datasetInfo, bands=bands, generate_name=generate_name,
                                     xmin=envelope[0],ymin=envelope[1],xmax=envelope[2],ymax=envelope[3])
    newSearchRequest.save()

    if (serviceType == 'WCS'):
        WCSNames = []
        periods=[]
        if int(byMonth) == 1:  # generate by month
            periods = general_utils.split_time_by_month(start, end)
        elif int(byYear)==1:
            periods=general_utils.split_time_by_year(start,end)
        elif int(byCustom)==1:
            periods=general_utils.split_time_by_custom(start,end)

        bandsName=str(bandsName).replace(';', '_')
        for period in periods:
            # store each dynamic WCS,record requestUuid and this Uuid, start, end, method (mean, max or min)
            curWCSUuid = general_utils.matchDatasetName(datasetName)+'_'+boundaryName+'_'+period['start_year']+period['start_month']+period[
                'start_day']+'_'+period['end_year']+period['end_month']+period['end_day']+'_'+bandsName+'_'+general_utils.getuuid12()
            WCSNames.append(curWCSUuid)
            startTime,endTime=period['start_year']+'-' +period['start_month'] +'-'+period['start_day'],period['end_year']+'-'+period['end_month']+'-'+period['end_day']
            newDynamicWcs = DynamicWcs(uuid=curWCSUuid, req_uuid=requestUuid, start=startTime, end=endTime)
            newDynamicWcs.save()

        responseDir = {}
        responseDir['code'] = 0
        responseDir['data'] = {}
        responseDir['data']['name']=generate_name
        responseDir['data']['result']=WCSNames
        return HttpResponse(str(responseDir))

# Generate WCS services
def generate_coverage_request(request):
    coverageName=request.GET.get("coverageName")
    print(coverageName)
    curWCS = DynamicWcs.objects.get(uuid=coverageName)

    curSearchRequest = SearchRequest.objects.get(uuid=curWCS.req_uuid) 
    content={}
    content['identifier']=coverageName
    content['xmin'],content['ymin']=str(curSearchRequest.xmin),str(curSearchRequest.ymin)
    content['xmax'],content['ymax']=str(curSearchRequest.xmax),str(curSearchRequest.ymax)
    docStr = generator.generate_service_description(
                'CoverageRequest', content, 'WCS')
    return HttpResponse(docStr, "text/xml")            

def get_coverage_service(request, dataset, type):
    docStr = ""
    if request.method == 'GET':
        service = request.GET.get('service')
        version = request.GET.get('version', default="1.1.0")
        requestType = request.GET.get('request')
        if (service is None) or (requestType is None):
            return HttpResponse("error")

        # WCS GetCapabilities
        if (str(requestType).lower() == 'getcapabilities'):
            if (str(type).lower() == 'wcs'):
                curSearchRequest = SearchRequest.objects.get(generate_name=dataset)
                geojsonData = curSearchRequest.boundary
                extent = general_utils.getBoundary(geojsonData)
                datasetName = curSearchRequest.dataset_name
                noCloud = curSearchRequest.no_cloud
                method = curSearchRequest.stacking_method

                curWCSs = DynamicWcs.objects.filter(req_uuid=curSearchRequest.uuid)
                content = {}
                content["serviceIdentification"] = {}
                content["serviceIdentification"][
                    "title"] = "Web Coverage Service for : (boundary:)"+curSearchRequest.boundary_name
                content["serviceIdentification"]["serviceType"] = "WCS"
                content["serviceIdentification"]["serviceTypeVersion"] = version
                content["serviceProvider"] = {}
                content["serviceProvider"]["providerName"] = "WS4GEE"
                content["serviceProvider"]["providerSite"] = PROJECT_ROOT_URL
                content["operationsMetadata"] = {}
                content["operationsMetadata"]["url"] = PROJECT_ROOT_URL+"/ws4gee/wcs?"
                content["operationsMetadata"]["operationName"] = ["GetCapabilities", "DescribeCoverage", "GetCoverage"]
                content["Contents"] = []
                for curWCS in curWCSs:
                    curCoverageSummary = {}
                    curCoverageSummary['title'] = curWCS.uuid
                    curCoverageSummary['abstract'] = 'Stacking method: '+method+'; no cloud:'+str(
                        bool(noCloud))+'; start time: '+curWCS.start+'; end time: '+curWCS.end+";"+curSearchRequest.abstract
                    curCoverageSummary['keywords'] = [
                        datasetName, "WCS", "GeoTIFF"]+eval(curSearchRequest.keywords)
                    curCoverageSummary['extent'] = extent
                    curCoverageSummary['identifier'] = curWCS.uuid
                    content["Contents"].append(curCoverageSummary)

                docStr = generator.generate_service_description(
                    'GetCapabilities', content, 'WCS')
        elif (str(requestType).lower() == 'describecoverage'):
            # WCS DescribeCoverage
            identifier = request.GET.get('identifiers')
            # Check if the xml exist in the Cache
            ############
            # docPath=None
            # ## Firstly search if it exists in the storage, if true return directly
            # if docPath!=None:
            #     responseXML= general_utils.readLocalFileToStr(docPath)
            #     return HttpResponse(responseXML, content_type='text/xml')
            ############
            # a new request
            if (identifier is None):
                return HttpResponse("error")
            curWCS = DynamicWcs.objects.get(uuid=identifier)
            if (curWCS is None):
                return HttpResponse("error")
            curSearchRequest = SearchRequest.objects.get(uuid=curWCS.req_uuid)
            datasetInfo, imageInfo = None, None
            if (curWCS.dataset_info is None):
                datasetInfo = gee_utils.getTargetDatasetInfo(general_utils.matchDatasetSnippetName(
                    curSearchRequest.dataset_name), curWCS.start, curWCS.end, curSearchRequest.boundary)
                curWCS.dataset_info = datasetInfo
                curWCS.save()
            else:
                datasetInfo = eval(curWCS.dataset_info)
            if (curWCS.image_info is None):
                imageInfo = gee_utils.getImageInfo(general_utils.matchDatasetSnippetName(curSearchRequest.dataset_name), curWCS.start,
                                                   curWCS.end, curSearchRequest.boundary, curSearchRequest.bands, curSearchRequest.stacking_method, curSearchRequest.no_cloud)
                curWCS.image_info = imageInfo
                curWCS.save()
            else:
                imageInfo = eval(curWCS.image_info)

            geojsonData = curSearchRequest.boundary
            extent = general_utils.getBoundary(geojsonData)
            usingImages = []
            for image in (datasetInfo['features']):
                usingImages.append(image["id"])

            content = {}
            content["title"] = identifier
            content["abstract"] = "Generate by images(id):" + \
                ";".join(usingImages)+';'+curSearchRequest.abstract
            if "keywords" in (datasetInfo['properties'].keys()):
                content['keywords'] = datasetInfo['properties']['keywords']+eval(curSearchRequest.keywords)
            else:
                content['keywords'] = ["WS4GEE", "GeoTIFF", "WCS"]
            content['identifier'] = identifier
            content['extent'] = extent
            if 'min' in imageInfo['bands'][0]['data_type']:
                content['minimumValue'] = str(
                    imageInfo['bands'][0]['data_type']['min'])
                content['maximumValue'] = str(
                    imageInfo['bands'][0]['data_type']['max'])
            else:
                content['minimumValue'] = "-Infinity"
                content['maximumValue'] = "Infinity"
            content["availableBands"] = eval(curSearchRequest.bands)
            docStr = generator.generate_service_description('DescribeCoverage', content, 'WCS')

    if request.method == 'POST':
        rawXML=""
        if ((request.content_type!='application/x-www-form-urlencoded') & (request.content_type!='form-data')):
            rawXML=request.body
        else:
            rawXML=request.POST.get('xml',0)
        if str(type) == 'wcs':
            # GetCoverage Method
            params = parser.retrieve_attr(rawXML, "GetCoverage")
            if ("error" in params.keys()):
                return HttpResponse('<error>{0}<error>'.format(params["error"]), "text/xml")
            tempImageName = general_utils.getuuid12()
            content = {}
            content["title"] = params["identifier"]
            content['abstract'] = "Generated from GEE. Please see check the status in the url: {0} . Then download after the generation completes.".format(
                PROJECT_ROOT_URL+"/status/"+tempImageName)
            content['identifier'] = params["identifier"]
            minX, minY, maxX, maxY = float(params['lowerCorner'][0]), float(
                params['lowerCorner'][1]), float(params['upperCorner'][0]), float(params['upperCorner'][1])

            curWCS = DynamicWcs.objects.get(uuid=params["identifier"])
            curSearchRequest = SearchRequest.objects.get(uuid=curWCS.req_uuid)
            content['resultUrl'] = File_ACCESS_PATH +  tempImageName+".tif"
            docStr = generator.generate_service_outcome("GetCoverage", content)

            # current  the resolution was set initially
            def func():
                curImage = gee_utils.getTargetImage(general_utils.matchDatasetSnippetName(curSearchRequest.dataset_name), curWCS.start,
                                                    curWCS.end, curSearchRequest.boundary, curSearchRequest.bands, curSearchRequest.stacking_method, curSearchRequest.no_cloud)
                gee_utils.generateUrlForTargetImage(256, curImage, tempImageName, minX, minY, maxX, maxY)
            thread = threading.Thread(target=func)
            thread.start()
            return HttpResponse(docStr, "text/xml")
    return HttpResponse(docStr, "text/xml")

# Generate WPS 1.0 services
def get_process_service(request):
    def get_DescribeProcess_response(identifiers):
        if (identifiers=='all'):
                identifiers=get_all_identifiers_list()
        else:
            identifiers = str(request.GET.get('identifier')).split(';')
            
        for identifier in identifiers:
            curContent = {}
            curProcess = Process.objects.get(name=identifier)
            curContent["identifier"] = curProcess.name
            curContent["title"] = curProcess.title
            if (curProcess.abstract is not None):
                curContent["abstract"] = curProcess.abstract
            curParams = ProcessParams.objects.filter(
                process_uuid=curProcess.uuid).order_by('order')
            params = []
            for curParam in curParams:
                paramDict = {}
                paramDict["identifier"] = curParam.param_name
                paramDict["title"] = curParam.title
                paramDict["paramType"] = curParam.param_type
                paramDict["dataType"] = curParam.data_type
                if (paramDict["paramType"]=='input'):
                    paramDict["minOccurs"] = int(curParam.min_occurs)
                    paramDict["maxOccurs"] = int(curParam.max_occurs)
                if (curParam.value_type == 2):    # 1:any_value;2:allowed_value;3:others
                    paramDict["allowedValue"] = str(
                        curParam.allowed_value).split(';')
                elif (curParam.value_type == 1):
                    paramDict["anyValue"] = curParam.any_value
                if (curParam.default_value is not None):
                    paramDict["defaultValue"] = curParam.default_value
                if (curParam.abstract is not None):
                    paramDict["abstract"] = curParam.abstract
                params.append(paramDict)
            curContent["params"] = params
            content.append(curContent)
        response = generator.generate_service_description(
                "DescribeProcess", content)
        return response

    def get_all_identifiers_list():
        identifier_list=[]
        processes=Process.objects.all()
        for process in processes:
            identifier_list.append(process.name)
        return identifier_list

    docStr = ""
    if request.method == 'GET':
        requestType = request.GET.get('request')
        # WPS GetCapabilities
        if (requestType.lower() == 'getcapabilities'):
            content = {}
            content["serviceIdentification"] = {}
            content["serviceIdentification"]["serviceType"] = "WPS"
            content["serviceIdentification"]["serviceTypeVersion"] = "1.0.0"
            content["serviceIdentification"]["title"] = "WS4GEE WPS v0.0.1-beta"
            content["serviceIdentification"]["abstract"] = "Services generated by WS4GEE from google earth engine"
            content["serviceProvider"] = {}
            content["serviceProvider"]["providerName"] = "WS4GEE"
            content["serviceProvider"]["providerSite"] = PROJECT_ROOT_URL
            content["operationsMetadata"] = {}
            content["operationsMetadata"]["url"] = PROJECT_ROOT_URL+"/ws4gee/wps"
            content["operationsMetadata"]["operationName"] = ["GetCapabilities", "DescribeProcess", "Execute"]
            content["processes"] = []
            curProcesses = Process.objects.all()
            for process in curProcesses:
                content["processes"].append(
                    {"identifier": process.name, "title": process.title})
            docStr = generator.generate_service_description(
                "GetCapabilities", content, "WPS")
            return HttpResponse(docStr, "text/xml")
        # WPS DescribeProcess
        elif (requestType == 'DescribeProcess'):
            content = []
            identifiers=str(request.GET.get('identifier'))
            
            docPath = None
            # Firstly search if it exists in the storage, if true return directly
            # if docPath!=None:
            #     doc= general_utils.readLocalFileToStr(docPath)
            #     return HttpResponse(doc,content_type='text/xml')
            # else:   # a new request
            docStr=get_DescribeProcess_response(identifiers)
            return HttpResponse(docStr, "text/xml")
        return
    # POST is for the Execute operation; however, actually getcapabilities/describeprocess can also be access by POST method
    if request.method == 'POST':
        rawXML=""
        if ((request.content_type!='application/x-www-form-urlencoded') & (request.content_type!='form-data')):
            rawXML=request.body
        else:
            rawXML=request.POST.get('xml',0)
        
        # update: using post method to access describeProcess
        if ("wps:describeprocess" in rawXML.lower()):
            curParamsDir = parser.retrieve_attr(rawXML, "DescribeProcess")
            identifier= curParamsDir["identifier"]
            docStr=get_DescribeProcess_response(identifiers)
            return HttpResponse(docStr, "text/xml")


        # otherwise this request is for "Execute"
        curParamsDir = parser.retrieve_attr(rawXML, "Execute")
        if ('error' in curParamsDir.keys()):
            return HttpResponse(curParamsDir['error'])
        identifier = curParamsDir["identifier"]
        curProcess = Process.objects.get(name=identifier)
        entrance_func = curProcess.entrance_func
        entrance_name = curProcess.entrance_name
        curProcessParams = ProcessParams.objects.filter(
            process_uuid=curProcess.uuid).order_by("order")
        usedScale = 30  # default scale
        usedBounds = ""
        paramsVariableList = []
        for i in range(0, len(curProcessParams)):
            paramName = curProcessParams[i].param_name
            for variable in curParamsDir['variables']:
                # export_scale,export_bounds are special issues
                if (variable["identifier"] == "export_scale"):
                    usedScale = float(variable["value"])
                    continue
                if (variable["identifier"] == "export_bounds"):
                    usedBounds = eval(
                        general_utils.readStrFromUrl(variable["value"]))
                    continue
                if (variable["identifier"] == paramName):
                    # model's parameter from DB
                    curType = curProcessParams[i].data_type
                    # A valid paramater must contain 'value'
                    if ('value' not in variable.keys()):
                        continue
                    # LiteralData can convert to 4 types
                    if curType == 'float' or curType == 'double':
                        paramsVariableList.append(float(variable["value"]))
                    elif curType == 'int':
                        paramsVariableList.append(int(variable["value"]))
                    elif curType == 'string':
                        paramsVariableList.append(str(variable["value"]))
                    elif curType == 'boolean':
                        paramsVariableList.append(bool(variable["value"]))

                    # For ComplexData, only the reference approach with text/plain was supported now
                    elif curType == 'Vector':
                        # temporarily accept only geojson from a url like - http://url/geom.geojson
                        if (variable["mimeType"] == "text/plain"):
                            geojsonData = general_utils.readStrFromUrl(
                                variable["value"])
                            paramsVariableList.append(parser.convert_to_ee_vector(
                                geojsonData, "geojson"))  # value is a url
                    elif curType == 'Raster': # currently accept .tif as raster input
                        paramsVariableList.append(parser.convert_by_ee_cloud(
                            variable["value"], variable["mimeType"]))
        # asynchronous way should be tried to split the output xml and the result
        # start to recording the execute state
        statusUuid = general_utils.getuuid12()
        curRecord = ExecuteStatusRecord(
            uuid=statusUuid, process_uuid=curProcess.uuid)
        curRecord.save()
        content = {"identifier": curProcess.name,
                   "title": curProcess.title, "statusUuid": statusUuid}
        docStr = generator.generate_service_outcome("Execute", content)


        # execute model
        model = __import__(entrance_name)
        f = getattr(model, entrance_func)
        result = f(*paramsVariableList)
         
        # Just one output is accepted; RawDataOutput is implemented 
        outputParam = ProcessParams.objects.get(
            process_uuid=curProcess.uuid, param_type='output')
        if (outputParam.data_type == "Vector"):
            tempVectorName=general_utils.getuuid12()
            curRecord.execution_uuid=tempVectorName
            url=gee_utils.generateUrlForVectorOutput(result,tempVectorName)
            curRecord.url=url
            curRecord.save()
            return HttpResponse(docStr, "text/xml")
        elif (outputParam.data_type == "Raster"):
            tempImageName = general_utils.getuuid12()
            curRecord.execution_uuid = tempImageName
            curRecord.save()
            def func():
                url=gee_utils.generateUrlForTargetImageWithBounds(
                    usedScale, result, tempImageName, usedBounds)
                curRecord.url=url
                curRecord.save()
            thread = threading.Thread(target=func)
            thread.start()

            return HttpResponse(docStr, "text/xml")
        else:
            return HttpResponse(result)


def check_coverage_status(request, uuid):
    list = DownloadingLog.objects.filter(
        image_uuid=uuid).order_by("create_time")
    if (len(list)>0):
        status = "Request "+list[len(list)-1].status
        print(status)
    if status == "":
        status == "Request Accepted"
    return HttpResponse(status)


def check_execute_status(request):
    curStatusUuid = request.GET.get("id")
    curStatus = ExecuteStatusRecord.objects.get(uuid=curStatusUuid)
    curProcess = Process.objects.get(uuid=curStatus.process_uuid)
    list = DownloadingLog.objects.filter(
        image_uuid=curStatus.execution_uuid).order_by("create_time")
    length=len(list)
    status=""
    if (length>0):
        status = list[length-1].status
    else:
        status=list[length].status
    content = {}
    content["statusUuid"] = curStatusUuid
    content["identifier"] = curProcess.name
    content["title"] = curProcess.title
    content["status"] = status
    content["output"]={}
    outputParam = ProcessParams.objects.get(
            process_uuid=curProcess.uuid, param_type='output')
    content["output"]["identifier"]=outputParam.param_name
    content["output"]["title"]=outputParam.title
    if (status == 'DOWNLOADED'):
        content["resultUrl"] = curStatus.url
        if ('.geojson' in content["resultUrl"]):
            content["mimeType"] = "application/json"
        elif ('.tif' in content["resultUrl"]):
            content["mimeType"] = "image/tiff"
        else:
            content["mimeType"] = "text/xml"

    docStr = generator.generate_service_outcome('ExecuteStatus', content)

    return HttpResponse(docStr, "text/xml")

def get_WCS_List(request):
    serviceList=[]
    list=DynamicWcs.objects.all().order_by("req_uuid")
    for curWcs in list:
        curGroup=SearchRequest.objects.get(uuid=curWcs.req_uuid)
        tempDir={}
        tempDir['name']=curWcs.uuid
        tempDir['type']='WCS'
        tempDir['group']=curGroup.generate_name
        tempDir['groupId']=curGroup.uuid
        tempDir['abstract']='test abstract'
        serviceList.append(tempDir)
    responseDir = {}
    responseDir['code'] = 0
    responseDir['data'] =serviceList
    return HttpResponse(str(responseDir))

def get_WPS_List(request):
    serviceList=[]
    list=Process.objects.all()
    for curWps in list:
        tempDir={}
        tempDir['name']=curWps.name
        tempDir['title']=curWps.title
        tempDir['type']='WPS'
        tempDir['abstract']=curWps.abstract
        tempDir['id']=curWps.uuid
        serviceList.append(tempDir)
    responseDir = {}
    responseDir['code'] = 0
    responseDir['data'] =serviceList
    return HttpResponse(str(responseDir))

def get_file(request):
    from django.http import StreamingHttpResponse
    def read_file(file_name,chunk_size=512):
        with open(file_name,"rb") as f:
            while True:
                c=f.read(chunk_size)
                if c:
                    yield c
                else:
                    break

    file=request.GET.get('fileName')
    fileName=""
    if (file=='tutorial'):
        fileName='Tutorial for WS4GEEClient.docx'
    elif (file=='instruction'):
        fileName="WS4GEEServer Instruction.docx"
    filePath=os.path.join(BASE_DIR,'static/tutorial',fileName)
    response=StreamingHttpResponse(read_file(filePath))
    response["Content-Type"]="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    response["Content-Disposition"]="attachment; filename={0}".format(fileName)
    response["Access-Control-Expose-Headers"]="Content-Disposition"
    return response

def get_zip_file(request):
    from django.http import StreamingHttpResponse
    def read_file(file_name,chunk_size=512):
        with open(file_name,"rb") as f:
            while True:
                c=f.read(chunk_size)
                if c:
                    yield c
                else:
                    break
    filePath=os.path.join(BASE_DIR,'static/tutorial',"Experiment Data.zip")
    response=StreamingHttpResponse(read_file(filePath))
    response["Content-Type"]="application/x-zip-compressed"
    response["Content-Disposition"]="attachment; filename={0}".format("Experiment Data.zip")
    response["Access-Control-Expose-Headers"]="Content-Disposition"
    return response
