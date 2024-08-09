from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

def get_exif_data(image):
    exif_data = {}
    try:
        info = image._getexif()
        if info:
            for tag, value in info.items():
                decoded = TAGS.get(tag, tag)
                exif_data[decoded] = value
    except AttributeError as e:
        print(f"Error retrieving EXIF data: {e}")
    return exif_data

def get_gps_info(exif_data):
    gps_info = {}
    if 'GPSInfo' in exif_data:
        for key in exif_data['GPSInfo'].keys():
            decoded = GPSTAGS.get(key, key)
            gps_info[decoded] = exif_data['GPSInfo'][key]
    return gps_info

def convert_gps(gps_info):
    try:
        if 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
            gps_latitude = gps_info['GPSLatitude']
            gps_longitude = gps_info['GPSLongitude']
            gps_latitude_ref = gps_info.get('GPSLatitudeRef', 'N')
            gps_longitude_ref = gps_info.get('GPSLongitudeRef', 'E')

            # Calculate latitude
            lat_degrees = gps_latitude[0]
            lat_minutes = gps_latitude[1]
            lat_seconds = gps_latitude[2]
            latitude = lat_degrees + (lat_minutes / 60.0) + (lat_seconds / 3600.0)
            if gps_latitude_ref == 'S':
                latitude = -latitude

            # Calculate longitude
            lon_degrees = gps_longitude[0]
            lon_minutes = gps_longitude[1]
            lon_seconds = gps_longitude[2]
            longitude = lon_degrees + (lon_minutes / 60.0) + (lon_seconds / 3600.0)
            if gps_longitude_ref == 'W':
                longitude = -longitude

            return latitude, longitude
        else:
            print("Error: GPS latitude or longitude information is missing.")
            return None
    except Exception as e:
        print(f"Error in convert_gps function: {e}")
        return None

# 이미지 파일 열기
image_path = "C:/Users/user/Desktop/image1.jpg"
image = Image.open(image_path)

# EXIF 데이터 가져오기
exif_data = get_exif_data(image)

# GPS 정보 추출
gps_info = get_gps_info(exif_data)

# GPS 정보 변환
if gps_info:
    latitude, longitude = convert_gps(gps_info)
    if latitude and longitude:
        print(f"Latitude: {latitude}, Longitude: {longitude}")
else:
    print("GPS 정보가 없습니다.")
