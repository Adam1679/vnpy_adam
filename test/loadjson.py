import json

path = '/home/hadoop/sc1812.json'
with open(path, 'r') as f:
    for data in f.readlines():
        json.loads(datae)
        # sdata = data.split(',')
        # sdata[0] = '{'
        # odata = ''
        # for i in sdata:
        #     if sdata.index(i) > 1:
        #         i = ','+i
        #     odata += i
        # print(odata)
        # print(json.loads(odata))


import random
random.randint()