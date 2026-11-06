
import urllib.request
url = 'https://d2qfwf04.eu1.hubspotlinks.com/Ctc/UB+113/d2qFWf04/VVrzTX3wQnpYW3sJ8G46XBLLFW3Bmyl95W-LvBN3V8l9C3qn9qW7Y8-PT6lZ3m0W1h_0c_5tDxR-MM0_QqqQzNVN34yqT6Kc9rTW3Ft4dz8ffj_9W1pPkdg4YSTFnW91cCwD1ydRVGVDW8Ht99N0c-W1XQFVC2TYTCxN5lQ64Rvlv1_W369C6B8T0SpfW3XvQ_W3RHLZhW2JJm2R625p5gW5XYXTC5pYdtfW58ljcn69s-wjW4fj-7f5bfd81W1Zdz4Q2NPTrrW1R8vpm9cjDk2W4HrbGP2t1FptW33XS722VwFk2W54QLgr2gt9DfVjPFh36dnNt0W4cH7Nl2SB3qCW89ftZ21WpzR6Vp1CcJ7wS5Z-W4fRlFT90l2PpW2Tn3-_5XTwtBdXrZTM04'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req)
body = resp.read().decode('utf-8', errors='ignore')
for line in body.splitlines():
    if 'targetURL' in line:
        print(line[:300])
