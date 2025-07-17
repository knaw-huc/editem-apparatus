import re
from collections import deque
from xml.sax import ContentHandler


class ApparatusHandler(ContentHandler):
    def __init__(self):
        self.html = ""
        self.capture = False
        self.parent_tag_stack = deque()
        self.close_tags = {}  # won't handle self-nested elements!
        self.unhandled_tags = set()

    def startDocument(self):
        pass

    def endDocument(self):
        if self.unhandled_tags:
            unhandled_tags_list = '\n'.join(sorted(self.unhandled_tags))
            self.html += f"<!-- unhandled tags:\n{unhandled_tags_list} -->"

    def startElement(self, tag, attributes):
        if tag == "titleStmt" or tag == "body":
            self.capture = True

        elif self.capture and tag == "bibl":
            if 'xml:id' in attributes:
                xml_id = attributes["xml:id"]
                self.html += f'<div class="bibl" id="{xml_id}">'
                self.close_tags[tag] = "</dd></div>"

        elif self.capture and tag == "label":
            if self.parent_tag_stack[-1] == "bibl":
                self.html += '<dt class="label">'
                self.close_tags[tag] = "</dt><dd>"
            else:
                self.html += '<dt class="label">'
                self.close_tags[tag] = "</dt>"

        elif self.capture and tag == "head":
            self.html += "<h3>"
            self.close_tags[tag] = "</h3>"

        elif self.capture and tag == "hi":
            rend = attributes["rend"]
            self.html += f'<span class="rend_{rend}">'
            self.close_tags[tag] = "</span>"

        elif self.capture and tag == "item":
            self.html += '<dd class="item">'
            self.close_tags[tag] = "</dd>"

        elif self.capture and tag == "list":
            if "type" in attributes:
                clazz = f'list_{attributes["type"]}'
            else:
                clazz = 'list'
            self.html += f'<dl class="{clazz}">'
            self.close_tags[tag] = "</dl>"

        elif self.capture and tag == "listBibl":
            self.html += '<dl class="listBibl">'
            self.close_tags[tag] = "</dl>"

        elif self.capture and tag == "p":
            if "rend" in attributes:
                rend = attributes["rend"]
                self.html += f'<p class="rend_{rend}">'
            else:
                self.html += "<p>"

            self.close_tags[tag] = "</p>"

        elif self.capture and tag == "title":
            if 'titleStmt' == self.parent_tag_stack[-1]:
                self.html += f"<h2>"
                self.close_tags[tag] = "</h2>"
            else:
                if 'level' in attributes:
                    clazz = f'title_{attributes["level"]}'
                else:
                    clazz = 'title'
                self.html += f'<span class="{clazz}">'
                self.close_tags[tag] = "</span>"

        else:
            if self.capture:
                self.unhandled_tags.add(tag)
                self.html += f"<!-- open  {tag} {attributes.keys()} -->"
        self.parent_tag_stack.append(tag)

    def endElement(self, tag):
        self.parent_tag_stack.pop()

        if tag == "body" or tag == "titleStmt":
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
            self.html += linkify_urls(content.lstrip())

    def processingInstruction(self, target, data):
        pass


# Match URLs starting with http(s) or www.
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
