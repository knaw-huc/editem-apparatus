import re
from collections import deque
from xml.sax import ContentHandler


class ApparatusHandler(ContentHandler):
    def __init__(self):
        self.html = ""
        self.capture = False
        self.stack = deque()
        self.close_tags = {}
        self.unhandled_tags = set()

    def startDocument(self):
        self.html += "<div>\n"

    def endDocument(self):
        self.html += "</div>\n"
        if self.unhandled_tags:
            unhandled_tags_list = '\n'.join(sorted(self.unhandled_tags))
            self.html += f"<!-- unhandled tags:\n{unhandled_tags_list} -->"

    def startElement(self, tag, attributes):
        self.stack.append(tag)
        if tag == "body":
            self.capture = True

        elif self.capture and tag == "bibl":
            if 'xml:id' in attributes:
                self.html += f"<div class='bibl' id='{attributes['xml:id']}'>"
                self.close_tags[tag] = "</div>"

        elif self.capture and tag == "label":
            self.html += "<div class='label'>"
            self.close_tags[tag] = "</div>"

        elif self.capture and tag == "head":
            self.html += "<h3>"
            self.close_tags[tag] = "</h3>"

        elif self.capture and tag == "hi":
            rend = attributes["rend"]
            self.html += f"<span class='rend_{rend}'>"
            self.close_tags[tag] = "</span>"

        elif self.capture and tag == "item":
            self.html += "<div class='item'>"
            self.close_tags[tag] = "</div>"

        elif self.capture and tag == "list":
            if "type" in attributes:
                clazz = f'list_{attributes["type"]}'
            else:
                clazz = 'list'
            self.html += f"<div class='{clazz}'>"
            self.close_tags[tag] = "</div>"

        elif self.capture and tag == "listBibl":
            self.html += "<div class='listBibl'>"
            self.close_tags[tag] = "</div>"

        elif self.capture and tag == "p":
            if "rend" in attributes:
                rend = attributes["rend"]
                self.html += f"<p class='rend_{rend}'>"
            else:
                self.html += "<p>"

            self.close_tags[tag] = "</p>"

        elif self.capture and tag == "title":
            if 'level' in attributes:
                clazz = f'title_{attributes["level"]}'
            else:
                clazz = 'title'
            self.html += f"<span class='{clazz}'>"
            self.close_tags[tag] = "</span>"

        else:
            if self.capture:
                self.unhandled_tags.add(tag)
                self.html += f"<!-- open  {tag} {attributes.keys()} -->"

    def endElement(self, tag):
        self.stack.pop()
        if tag == "body":
            self.capture = False
        else:
            if self.capture:
                if tag in self.close_tags:
                    self.html += self.close_tags[tag]
                    self.close_tags.pop(tag)
                else:
                    self.html += f"<!-- close {tag} -->\n"

    def characters(self, content):
        if self.capture:
            self.html += linkify_urls(content)

    def processingInstruction(self, target, data):
        pass


# Regex pattern to match URLs (http, https, or www)
url_pattern = re.compile(
    r'(?P<url>(https?://|www\.)[^\s<>"\'()]+)',
    re.IGNORECASE
)


def linkify_urls(text: str) -> str:
    # Replacement function to wrap the URL in an anchor tag
    def replace_with_link(match):
        url = match.group('url')
        href = url if url.startswith('http') else f'https://{url}'
        return f'<a href="{href}" target="_blank">{url}</a>'

    # Substitute all URLs with HTML links
    return url_pattern.sub(replace_with_link, text)
