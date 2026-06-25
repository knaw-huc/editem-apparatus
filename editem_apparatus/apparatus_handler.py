import html
from collections import deque
from xml.sax import ContentHandler

from editem_apparatus.utils import linkify_urls


class ApparatusHandler(ContentHandler):
    def __init__(self):
        self.html_string = ""
        self.capture = False
        self.parent_tag_stack = deque()
        self.close_tags = {}
        self.unhandled_tags = set()

    def startDocument(self):
        pass

    def endDocument(self):
        if self.unhandled_tags:
            unhandled_tags_list = '\n  '.join(sorted(self.unhandled_tags))
            self.html_string += f"\n<!--\nunhandled tags:\n  {unhandled_tags_list}\n-->"

    def startElement(self, name, attrs):
        if name == "titleStmt" or name == "body":
            self.capture = True

        elif self.capture and name == "bibl":
            if 'xml:id' in attrs:
                xml_id = attrs["xml:id"]
                self.html_string += f'<div class="bibl" id="{xml_id}">'
                self.close_tags[name] = "</div>"

        elif self.capture and name == "label":
            self.html_string += '<div class="label">'
            self.close_tags[name] = "</div>"

        elif self.capture and name == "head":
            self.html_string += "<h3>"
            self.close_tags[name] = "</h3>"

        elif self.capture and name == "hi":
            rend = attrs["rend"]
            self.html_string += f'<span class="rend_{rend}">'
            self.close_tags[name] = "</span>"

        elif self.capture and name == "item":
            self.html_string += '<div class="item">'
            self.close_tags[name] = "</div>"

        elif self.capture and name == "list":
            if "type" in attrs:
                clazz = f'list_{attrs["type"]}'
            else:
                clazz = 'list'
            self.html_string += f'<div class="{clazz}">'
            self.close_tags[name] = "</div>"

        elif self.capture and name == "listBibl":
            if 'xml:id' in attrs:
                xml_id = attrs["xml:id"]
                self.html_string += f'<div class="listBibl" id="{xml_id}">'
            else:
                #MAYBE TODO: is the xml:id essential? do we want instead want to raise an error if it is missing?
                self.html_string += f'<div class="listBibl">'
            self.close_tags[name] = "</div>"

        elif self.capture and name == "p":
            if "rend" in attrs:
                rend = attrs["rend"]
                self.html_string += f'<p class="rend_{rend}">'
            else:
                self.html_string += "<p>"

            self.close_tags[name] = "</p>"

        elif self.capture and name == "title":
            if 'titleStmt' == self.parent_tag_stack[-1]:
                self.html_string += "<h2>"
                self.close_tags[name] = "</h2>"
            else:
                if 'level' in attrs:
                    clazz = f'title_{attrs["level"]}'
                else:
                    clazz = 'title'
                self.html_string += f'<span class="{clazz}">'
                self.close_tags[name] = "</span>"
                # ic(tag, self.close_tags)

        else:
            if self.capture:
                self.unhandled_tags.add(name)
                self.html_string += f"<!-- open {name} {attrs.keys()} -->"
        self.parent_tag_stack.append(name)

    def endElement(self, name):
        self.parent_tag_stack.pop()

        if name == "body" or name == "titleStmt":
            self.capture = False
        else:
            if self.capture:
                if name in self.close_tags:
                    self.html_string += self.close_tags[name]
                    self.close_tags.pop(name)
                else:
                    # if self.close_tags:
                    #     ic(tag, self.close_tags)
                    self.html_string += f"<!-- close {name} -->\n"

    def characters(self, content):
        if self.capture:
            self.html_string += linkify_urls(html.escape(content))

    def processingInstruction(self, target, data):
        pass
