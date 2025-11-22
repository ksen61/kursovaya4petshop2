from django import template
register = template.Library()

@register.filter
def user_date(value, user):
    if not value:
        return ""
    fmt = getattr(user.profile, 'date_format', '%d.%m.%Y')
    return value.strftime(fmt)