# 카카오API를 사용하여 좌표->주소 변환
import json
import pprint
import requests


def get_address(lat, lng):
    url = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?x="+lng+"&y="+lat
    # 'KaKaoAK '는 그대로 두시고 개인키만 지우고 입력해 주세요.
    # ex) KakaoAK 6af8d4826f0e56c54bc794fa8a294
    headers = {"Authorization": "KakaoAK 47016d6fd880e9e9b236c571fa9ff0b2"}
    api_json = requests.get(url, headers=headers)
    full_address = json.loads(api_json.text)

    return full_address


def get_nearby_places(latitude, longitude, query):
    api_key = '47016d6fd880e9e9b236c571fa9ff0b2'
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"

    params = {
        'query': query,  # 빈 문자열로 설정하여 모든 장소 검색
        'x': longitude,
        'y': latitude,
        'radius': 100  # 검색 반경 (미터 단위)
    }

    headers = {
        "Authorization": f"KakaoAK {api_key}"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        places = response.json()
        return places
    else:
        print(f"Error: {response.status_code}")
        return None

full_address = get_address('37.4220936', '-122.083922')

places_info1 = get_nearby_places('37.4220936', '-122.083922', '관광명소')
places_info2 = get_nearby_places('37.4220936', '-122.083922', '음식점')

if places_info1:
    print(places_info1)
if places_info2:
    print(places_info2)


real = full_address['documents']

for item in real:
    do = item['region_1depth_name']
    si = item['region_2depth_name']
    upmyondong = item['region_3depth_name']
    ri = item['region_4depth_name']
    print(do, si, upmyondong, ri)

# do = real['region_1depth_name']
# si = real['region_2depth_name']
# upmyondong = real['region_3depth_name']
# ri = real['region_4depth_name']
# print(do, si, upmyondong, ri)

pprint.pprint(full_address)