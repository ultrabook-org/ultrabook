import re
from django import template

register = template.Library()

@register.filter(is_safe=True)
def strip_thoughts(value):
    """
    Remove any single <think>…</think> block (including its contents)
    from the passed string.
    """
    # non-greedy, DOTALL so that newlines are matched
    return re.sub(r'<think>.*?</think>', '', value, flags=re.DOTALL)

@register.filter(is_safe=True)
def extract_thoughts(value):
    """
    Return only the contents between a single <think>…</think> block,
    or the empty string if none is found.
    """
    m = re.search(r'<think>(.*?)</think>', value, flags=re.DOTALL)
    return m.group(1) if m else ''