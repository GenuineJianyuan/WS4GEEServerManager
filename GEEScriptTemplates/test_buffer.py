import ee
import os

# os.environ['HTTP_PROXY']="http://127.0.0.1:7890"
# os.environ['HTTPS_PROXY']='http://127.0.0.1:7890'

ee.Initialize()

def entrance(vector,distance_in_meters):
    fc=ee.FeatureCollection(vector)
    buff=fc.geometry().buffer(distance_in_meters)
    return buff
