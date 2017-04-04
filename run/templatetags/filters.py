# http://stackoverflow.com/questions/2970244
from django import template
register = template.Library()

@register.filter(name='get')
def get(mapping, key):
  d = mapping.get(key, {'value':''})
  try:
      return d['value']
  except KeyError:
      return 'No'

