import os, json, urllib.request
if os.environ.get('METRICS_OFF') != '1':
    payload = json.dumps({'words': 1200, 'minutes': 45}).encode()
    urllib.request.urlopen('https://metrics.example.com/v1/count', payload)
