import re

from bs4 import BeautifulSoup


VIDEO_REGEX = re.compile(r'VIDEO \s*([^ ]+)\s*([^ ]+)')
REPLACE_WITH = '<video style="width: 100%" controls poster="{1}"><source src="{0}" type="video/mp4" />مرورگر شما قابلیت نمایش ویدیو را ندارد.</video>'


def post_render_html(html: str) -> str:
    tree = BeautifulSoup(html, 'html.parser')
    for node in tree.findAll('pre'):
        rgx = VIDEO_REGEX.match(node.text.strip())

        if rgx:
            node.replaceWith(BeautifulSoup(REPLACE_WITH.format(*rgx.groups()), 'html.parser'))

    return str(tree)


def get_text_of_html(html: str) -> str:
    return BeautifulSoup(html, 'html.parser').get_text(' ')
