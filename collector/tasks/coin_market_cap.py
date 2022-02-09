import requests
from celery import shared_task

from collector.models import CoinMarketCap


@shared_task()
def update_coin_market_cap():

    old = b'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n<svg xmlns:xlink="http://www.w3.org/1999/xlink" height="48px" version="1.1" viewBox="0 0 164 48" width="164px" x="0px" y="0px" xmlns="http://www.w3.org/2000/svg">\n  <defs>\n    <clipPath id="clip-1642496000">\n      <rect height="48" width="164" x="0" y="0"/>\n    </clipPath>\n  </defs>\n  <rect height="48" style="fill:rgb(255,255,255);fill-opacity:0;stroke:none;" width="164" x="0" y="0"/>\n  <rect height="48" style="fill:rgb(255,255,255);fill-opacity:0;stroke:none;" width="164" x="0" y="0"/>\n  <g clip-path="url(#clip-1642496000)">\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="6.560000000000002" x2="13.744761904761907" y1="1.920000000000002" y2="5.065312983057993"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="13.744761904761907" x2="20.92952380952381" y1="5.065312983057993" y2="12.018140177901003"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="20.92952380952381" x2="28.114285714285714" y1="12.018140177901003" y2="18.41644828812103"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="28.114285714285714" x2="35.29904761904762" y1="18.41644828812103" y2="21.47173824818279"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="35.29904761904762" x2="42.483809523809526" y1="21.47173824818279" y2="26.760338781009473"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="42.483809523809526" x2="49.668571428571425" y1="26.760338781009473" y2="46.08"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="49.668571428571425" x2="56.85333333333333" y1="46.08" y2="24.082042742944587"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="56.85333333333333" x2="64.03809523809524" y1="24.082042742944587" y2="28.95670643209809"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="64.03809523809524" x2="71.22285714285714" y1="28.95670643209809" y2="35.69379588216338"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="71.22285714285714" x2="78.40761904761905" y1="35.69379588216338" y2="42.15905547628683"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="78.40761904761905" x2="85.59238095238095" y1="42.15905547628683" y2="24.31468658803379"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="85.59238095238095" x2="92.77714285714285" y1="24.31468658803379" y2="26.534217805654468"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="92.77714285714285" x2="99.96190476190476" y1="26.534217805654468" y2="39.12200098026446"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="99.96190476190476" x2="107.14666666666666" y1="39.12200098026446" y2="34.230507900612736"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="107.14666666666666" x2="114.33142857142857" y1="34.230507900612736" y2="28.766276545807614"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="114.33142857142857" x2="121.51619047619047" y1="28.766276545807614" y2="24.664072292238618"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="121.51619047619047" x2="128.7009523809524" y1="24.664072292238618" y2="23.993488733172892"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="128.7009523809524" x2="135.88571428571427" y1="23.993488733172892" y2="23.103629857954317"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="135.88571428571427" x2="143.0704761904762" y1="23.103629857954317" y2="23.96077373296556"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="143.0704761904762" x2="150.2552380952381" y1="23.96077373296556" y2="23.973480155919244"/>\n    <line style="fill:none;stroke:rgb(237,194,64);stroke-width:2;stroke-miterlimit:10;stroke-linecap:round;" x1="150.2552380952381" x2="157.44" y1="23.973480155919244" y2="20.650309358745716"/>\n  </g>\n</svg>\n'

    r = requests.get('https://s3.coinmarketcap.com/generated/sparklines/web/1d/2781/1839.svg')

    if r.content != old:
        print('NNNNNNNNNNNNNNNNNNNNNN')

    coins = CoinMarketCap.request()
    id_to_coin = {c['id']: c for c in coins}

    objects = CoinMarketCap.objects.all()

    for obj in objects:
        data = id_to_coin.get(obj.internal_id)
        if data:
            price_info = data['quotes'][0]

            obj.change_24h = price_info['percentChange24h']
            obj.volume_24h = price_info['volume24h']

    CoinMarketCap.objects.bulk_update(objects, fields=['change_24h', 'volume_24h'])
