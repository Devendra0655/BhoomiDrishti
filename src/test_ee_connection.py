import ee

# Try to connect using your registered project
ee.Initialize(project='bhoomidrishti')

# Ask Earth Engine for something simple to prove the connection works
image = ee.Image('USGS/SRTMGL1_003')
print("Connected successfully!")
print("Image info:", image.getInfo()['bands'][0]['id'])