from GEEUtils.runtime import ee,json,os
from google.cloud import storage
from Model.models import DownloadingLog
import time
from WS4GEEServerManager.settings import FILE_SAVE_PATH,File_ACCESS_PATH

from Utils import general_utils

def maskL8sr(image):
  #    Bits 3 and 5 are cloud shadow and cloud, respectively.
  cloudShadowBitMask = (1 << 3)
  cloudsBitMask = (1 << 5)
  #    Get the pixel QA band.
  qa = image.select('pixel_qa')
  #    Both flags should be set to zero, indicating clear conditions.
  mask = qa.bitwiseAnd(cloudShadowBitMask).eq(0).And(qa.bitwiseAnd(cloudsBitMask).eq(0))
  return image.updateMask(mask)

def maskL457(image):
  qa = image.select('pixel_qa')
  #    If the cloud bit (5) is set and the cloud confidence (7) is high
  #    or the cloud shadow bit is set (3), then it's a bad pixel.
  cloud = qa.bitwiseAnd(1 << 5).And(qa.bitwiseAnd(1 << 7)).Or(qa.bitwiseAnd(1 << 3))
  #    Remove edge pixels that don't occur in all bands
  mask2 = image.mask().reduce(ee.Reducer.min())
  return image.updateMask(cloud.Not()).updateMask(mask2)

def generateEEFeaturesFromJSON(geojsonData):
    geojson=json.loads(geojsonData)
    features=None
    if geojson["type"] == "FeatureCollection":
        features = ee.FeatureCollection(geojson["features"])
    return features

def generateEERasterFromCloud(eeCloudPath):
    image=ee.Image.loadGeoTIFF(eeCloudPath)
    return image

def generateEERasterFromCloudTest(eeCloudPath):
    image=ee.Image.loadGeoTIFF(eeCloudPath)
    return image.getInfo()

def getTargetDatasetInfo(datasetName,start,end,geojsonData):
    geojson=json.loads(geojsonData)
    features=None
    if geojson["type"] == "FeatureCollection":
        features = ee.FeatureCollection(geojson["features"])
    dataset = ee.ImageCollection(datasetName).filterDate(start, end).filterBounds(features)
    return dataset.getInfo()

def getTargetImage(datasetName,start,end,geojsonData,bands='All',method='mean',no_cloud=1):
    geojson=json.loads(geojsonData)
    features=None
    if geojson["type"] == "FeatureCollection":
        features = ee.FeatureCollection(geojson["features"])
    dataset = ee.ImageCollection(datasetName).filterDate(start, end).filterBounds(features)
    if (no_cloud==1):
        if (datasetName.find("LC08")!=-1):
            dataset=dataset.map(maskL8sr)
        elif (datasetName.find("LT05")!=-1):
            dataset=dataset.map(maskL457)
    out_image=None
    
    if method=='mean':
        out_image=ee.Image(dataset.mean()).clip(features)
    elif method=='min':
        out_image=ee.Image(dataset.min()).clip(features)
    elif method=='max':
        out_image=ee.Image(dataset.max()).clip(features)
    if bands!='All':
        curBands=(eval(bands))
        out_image=ee.Image(out_image).select(curBands)
    return out_image

def getImageInfo(datasetName,start,end,geojsonData,bands='All',method='mean',no_cloud=1):
    image=getTargetImage(datasetName,start,end,geojsonData,bands,method,no_cloud)
    return image.getInfo()

def upload_blob(bucket_name, source_file_name, destination_blob_name):
    #     """Uploads a file to the bucket."""
    #     # The ID of your GCS bucket
    #     # bucket_name = "your-bucket-name"
    #     # The path to your file to upload
    #     # source_file_name = "local/path/to/file"
    #     # The ID of your GCS object
    #     # destination_blob_name = "storage-object-name"
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    print(
        "File {} uploaded to {}.".format(
            source_file_name, destination_blob_name
        )
    )
    return "gs://"+bucket_name+"/"+destination_blob_name

def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"

    # The ID of your GCS object
    # source_blob_name = "storage-object-name"

    # The path to which the file should be downloaded
    # destination_file_name = "local/path/to/file"
    index = source_blob_name.rfind('.')
    name = source_blob_name[:index]
    curLog=DownloadingLog(uuid=general_utils.getuuid12(),image_uuid=name,status="DOWNLOADING")
    curLog.save()
    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    # Construct a client side representation of a blob.
    # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
    # any content from Google Cloud Storage. As we don't need additional data,
    # using `Bucket.blob` is preferred here.
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

    print(
        "Downloaded storage object {} from bucket {} to local file {}.".format(
            source_blob_name, bucket_name, destination_file_name
        )
    )
    curLog=DownloadingLog(uuid=general_utils.getuuid12(),image_uuid=name,status="DOWNLOADED")
    curLog.save()

def export_gee_image(image,name,scale,region):
    task = ee.batch.Export.image.toCloudStorage(
       image=image,
       bucket='image_bucket_leismars',
       fileNamePrefix=name,
       scale=scale,
       region=region)
    task.start()
    state=""
    while state!='COMPLETED':
        curLog=DownloadingLog(uuid=general_utils.getuuid12(),image_uuid=name,status=state)
        curLog.save()
        state=task.status()['state']
        time.sleep(15)
    curLog=DownloadingLog(uuid=general_utils.getuuid12(),image_uuid=name,status=state+" IN THE CLOUD")
    curLog.save()
    print("Success")
    return 1

def generateUrlForTargetImage(scale,curImage,tempImageName,minX,minY,maxX,maxY):
    curImage=ee.Image(curImage)
    region=ee.Geometry.Rectangle([minX,minY,maxX,maxY])
    rasterSaveName=tempImageName+".tif"
    export_gee_image(curImage,tempImageName,scale,region) 
    download_blob("image_bucket_leismars", rasterSaveName, os.path.join(FILE_SAVE_PATH,rasterSaveName))
    return File_ACCESS_PATH+rasterSaveName


def generateUrlForTargetImageWithBounds(scale,curImage,tempImageName,bounds):
    region = ee.FeatureCollection(bounds["features"]).geometry()
    curImage=ee.Image(curImage)
    rasterSaveName=tempImageName+".tif"
    export_gee_image(curImage,tempImageName,scale,region)
    download_blob("image_bucket_leismars", rasterSaveName, os.path.join(FILE_SAVE_PATH,rasterSaveName))
    return File_ACCESS_PATH+rasterSaveName

def generateUrlForVectorOutput(vector,fileName):
    # suppose the size of the output vector is small, use getDownloadURL (faster), or 
    # the google cloud should be used (slower)
    vectorSaveName=fileName+".geojson"
    curLog=DownloadingLog(uuid=general_utils.getuuid12(),image_uuid=fileName,status="READY")
    curLog.save()
    url=ee.FeatureCollection(vector).getDownloadURL(filetype="geojson",filename=fileName)
    curLog=DownloadingLog(uuid=general_utils.getuuid12(),image_uuid=fileName,status="COMPLETED IN THE CLOUD")
    curLog.save()
    general_utils.readFileFromUrl(url,vectorSaveName,FILE_SAVE_PATH)
    curLog=DownloadingLog(uuid=general_utils.getuuid12(),image_uuid=fileName,status="DOWNLOADED")
    curLog.save()
    return File_ACCESS_PATH+vectorSaveName

def getBoundaryBox(geojson):
    fc=generateEEFeaturesFromJSON(geojson)
    envelope=fc.geometry().bounds()
    min,max=envelope.getInfo()['coordinates'][0][0],envelope.getInfo()['coordinates'][0][2]
    xmin,ymin,xmax,ymax=min[0],min[1],max[0],max[1]
    return [xmin,ymin,xmax,ymax]