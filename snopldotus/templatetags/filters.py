import itertools
from django import template
register = template.Library()

from django.conf import settings
import dateutil
import pytz
import re

# http://stackoverflow.com/questions/2970244
@register.filter(name='get')
def get(mapping, key):
  d = mapping.get(key, {'value':''})
  try:
      return d['value']
  except KeyError:
      return 'No'

@register.filter(name='get2')
def get2(mapping, key):
    #return mapping.get(key, '')
    try:
        return mapping[key]
    except IndexError:
        return None
    except KeyError:
        return None
    except Exception:
        return None

@register.filter(name='date_format')
def date_format(s):
    tz = pytz.timezone(settings.PHILA_TZ)
    fmt = '%Y/%m/%d %H:%M:%S (%Z)'
    utctime = dateutil.parser.parse(s, fuzzy=True)
    if utctime.tzinfo is None:
        utctime = (pytz.timezone('UTC')).localize(utctime)
    return utctime.astimezone(tz).strftime(fmt)

@register.filter('bit_and')
def bit_and(x, y):
    y = int(y, 16)
    return x & y


@register.filter('subtract')
def subtract(x, y):
    return x - y


@register.filter('multiply')
def multiply(x, y):
    return x * y


@register.filter('mod')
def modulus(x, y):
    return x % y

@register.filter('grouper')
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    if iterable is None:
        return None
    args = [iter(iterable)] * n
    return itertools.izip_longest(fillvalue=fillvalue, *args)


@register.filter('get_range')
def get_range(x):
    return range(x)


@register.filter('min')
def minimum(x, y):
    return min(x, y)


@register.filter('max')
def maximum(x, y):
    return max(x, y)


mappings = (
    # Links
    (r'http://[^ ,]*',
     lambda x: '<a href="%s">%s</a>' % (x.group(0), x.group(0))),
    (r'\b(?!feed|ffff|dead)([f|d][0-9a-fA-F]{3})\b',
     lambda x: '<a href="/debugdb/board/%s">%s</a>' % (x.group(0), x.group(0))),
    (r'\bx(andy|bill|boardx|cam|doublebeta|eugene|failure|gabriel|heintzelman|indium|josh|knapik|laurentian|mastbaum|noel|orebigann|penn|queens|richie|shokair|tim|u238|vanberg|washinton|yak)\b',
     lambda x: '<a href="/debugdb/board/%s">%s</a>' % (x.group(0), x.group(0))),
    (r'{{(.*)}}',
     lambda x: '<b>%s</b>' % x.group(1)),
)

@register.filter(name='keywords')
def keywords(text):
    for e, r in mappings:
        text = re.sub(e, r, text)
    return text

