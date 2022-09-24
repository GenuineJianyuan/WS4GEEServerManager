import ee

ee.Initialize()

def entrance(raster1,raster2):
    return ee.Image(raster1).add(ee.Image(raster2))
