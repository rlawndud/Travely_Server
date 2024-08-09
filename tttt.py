sql = 'select * from Images where teamNo = ? '

print(sql)

ad = 'or teamNo = ? '

ifff = 'and Image_No > ?'

end = ';'


team = [10, 11, 23, 24]

team_tuple = tuple(team)

print(team_tuple)

realadd = ad * (len(team) - 1)

realsql = sql + realadd

# 문자열 끝의 공백 제거
query = realsql.strip()

realquery = query + end

print(realquery)

