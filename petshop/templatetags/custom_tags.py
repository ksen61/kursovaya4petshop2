from django import template

register = template.Library()

@register.filter
def pluck(list_of_dicts, key):
    return [d.get(key) for d in list_of_dicts]

@register.filter
def get_attr_field(obj, attr):
    return getattr(obj, attr)

@register.filter
def get_item(dictionary, key):
    if dictionary and key:
        return dictionary.get(key, key)
    return key