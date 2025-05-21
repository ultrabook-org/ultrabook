from django import template
from django.utils.safestring import mark_safe

import markdown
import bleach

register = template.Library()

@register.filter
def markdownify(text):
    # Convert markdown to HTML
    html = markdown.markdown(text)
    
    # Sanitize HTML to prevent XSS
    # Allow all standard HTML tags and attributes
    clean_html = bleach.clean(
        html,
        tags=[
            'p', 'strong', 'em', 'code', 'a', 'ul', 'li', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'blockquote', 'hr', 'pre', 'div', 'img', 'table', 'tr', 'td', 'th', 'thead', 'tbody', 'tfoot', 'caption', 'colgroup', 'col'
        ],
        attributes={
            'a': ['href', 'title'],
            'img': ['src', 'alt', 'title'],
            'table': ['border', 'cellpadding', 'cellspacing'],
            'td': ['colspan', 'rowspan'],
            'th': ['colspan', 'rowspan'],
            'tr': ['rowspan'],
            'div': ['class'],
            'span': ['class'],
            'code': ['class'],
            'pre': ['class'],
        },
        protocols=['http', 'https'],
        strip=True
    )
    return mark_safe(clean_html)