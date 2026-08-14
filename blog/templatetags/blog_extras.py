from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def markdown_body(value):
    import markdown

    html = markdown.markdown(
        value or "",
        extensions=["fenced_code", "tables", "nl2br", "sane_lists"],
    )
    return mark_safe(html)
