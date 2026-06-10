import re
from collections import deque
from xml.sax import ContentHandler

from loguru import logger

TARGET = "target"
FACET_ID = "facetID"


class HomeHandler(ContentHandler):
    def __init__(self):
        self.html = ""
        self.capture = False
        self.parent_tag_stack = deque()
        self.close_tags = {}
        self.unhandled_tags = set()

    def startDocument(self):
        pass

    def endDocument(self):
        if self.unhandled_tags:
            unhandled_tags_list = '\n'.join(sorted(self.unhandled_tags))
            self.html += f"<!-- unhandled tags:\n{unhandled_tags_list} -->"

    def startElement(self, tag, attributes):
        if tag == "body":
            self.capture = True

        elif self.capture and tag == "bibl":
            if 'xml:id' in attributes:
                xml_id = attributes["xml:id"]
                self.html += f'<div class="bibl" id="{xml_id}">'
                self.close_tags[tag] = "</div>"

        elif self.capture and tag == "div":
            div_class = "div"
            if "type" in attributes:
                div_class = attributes["type"]
            self.html += f'<div class="{div_class}">'
            self.close_tags[tag] = "</div>"

        elif self.capture and tag == "ed:search":
            if FACET_ID in attributes and TARGET in attributes:
                facetId = attributes[FACET_ID]
                target = attributes[TARGET]
                facet = f"{facetId}Id"
                facet_value = target.split("#")[-1]
                href = f"?query[terms][{facet}][]={facet_value}"
                self.html += f'<a href="{href}">'
                self.close_tags[tag] = "</a>"
            else:
                logger.warning(
                    f"{tag} element should have both `{FACET_ID}` and `{TARGET}` attributes, attributes found: {attributes.keys()}")

        elif self.capture and tag == "head":
            level = attributes["level"]
            self.html += f"<{level}>"
            self.close_tags[tag] = f"</{level}>"

        elif self.capture and tag == "hi":
            rend = attributes["rend"]
            self.html += f'<span class="rend_{rend}">'
            self.close_tags[tag] = "</span>"

        elif self.capture and tag == "item":
            self.html += '<div class="item">'
            self.close_tags[tag] = "</div>"

        elif self.capture and tag == "label":
            self.html += '<div class="label">'
            self.close_tags[tag] = "</div>"

        elif self.capture and tag == "list":
            if "type" in attributes:
                clazz = f'list_{attributes["type"]}'
            else:
                clazz = 'list'
            self.html += f'<div class="{clazz}">'
            self.close_tags[tag] = "</div>"

        elif self.capture and tag == "listBibl":
            xml_id = attributes["xml:id"]
            self.html += f'<div class="listBibl" id="{xml_id}">'
            self.close_tags[tag] = "</div>"

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
                # ic(tag, self.close_tags)

        else:
            if self.capture:
                self.unhandled_tags.add(tag)
                # self.html += f"<!-- open {tag} {attributes.keys()} -->"
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
                # else:
                #     # if self.close_tags:
                #     #     ic(tag, self.close_tags)
                #     self.html += f"<!-- close {tag} -->\n"

    def characters(self, content):
        if self.capture:
            self.html += linkify_urls(html.escape(content))

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
