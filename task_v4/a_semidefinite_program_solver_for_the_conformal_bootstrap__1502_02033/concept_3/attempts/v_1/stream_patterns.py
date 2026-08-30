import json


source = json.load(open('patterns.json'))
result = {}
for pattern in source:
    for offset in range(len(pattern['values']) - 11):
        packed = 0
        for value in pattern['values'][offset:offset + 12]:
            packed = packed * 11 + value + 5
        result[packed] = {'pattern': pattern, 'offset': offset}
json.dump(result, open('stream_patterns.json', 'w'))
with open('stream_patterns.txt', 'w') as output:
    output.write('\n'.join(map(str, result)))
