# Match URLs starting with http(s) or www.
import re

url_pattern = re.compile(
    r'(?P<url>(https?://|www\.)[^\s<>"\'()]+[^\s<>"\'(),.!?;:\]])?',
    re.IGNORECASE
)


def linkify_urls(text: str) -> str:
    def replace_with_link(match):
        url = match.group('url')
        if not url:
            return match.group(0)
        href = url if url.startswith('http') else f'https://{url}'
        return f'<a href="{href}" target="_blank">{url}</a>'

    return url_pattern.sub(replace_with_link, text)
