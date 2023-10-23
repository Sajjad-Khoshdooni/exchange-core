import re

from bs4 import BeautifulSoup


VIDEO_REGEX = re.compile(r'VIDEO\s+([^ ]+)\s+([^ ]+)')
REPLACE_WITH = '<video style="width: 100%" controls poster="{1}"><source src="{0}" type="video/mp4" />مرورگر شما قابلیت نمایش ویدیو را ندارد.</video>'

EMPTY_STYLE_REGEX = re.compile(r' style=\"\s*\"')


def post_render_html(html: str) -> str:
    html = html.replace('color: rgb(0, 0, 0);', '').replace('background-color: transparent;', '')
    html = EMPTY_STYLE_REGEX.sub("", html)
    tree = BeautifulSoup(html, 'html.parser')
    for node in tree.findAll('pre'):
        rgx = VIDEO_REGEX.match(node.text.strip())

        if rgx:
            node.replaceWith(BeautifulSoup(REPLACE_WITH.format(*rgx.groups()), 'html.parser'))

    return str(tree)


def get_text_of_html(html: str) -> str:
    return BeautifulSoup(html, 'html.parser').get_text(' ')
