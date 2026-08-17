from django import template

register = template.Library()


@register.filter
def get_attr(obj, attr_name):
    try:
        value = getattr(obj, attr_name, "")
        
        # Handle ManyToMany fields (RelatedManager)
        if hasattr(value, 'all') and callable(value.all):
            items = list(value.all())
            if not items:
                return "—"
            return ", ".join(str(i) for i in items)
            
        if callable(value):
            value = value()
            
        if value is True:
            return "✅"
        if value is False:
            return "—"
        if value in (None, ""):
            return "—"
        return value
    except Exception:
        return "—"
