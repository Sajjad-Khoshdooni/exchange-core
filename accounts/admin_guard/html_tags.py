from django.utils.safestring import mark_safe


def anchor_tag(title, url, style="", target="", _class=""):
    return mark_safe("<a href='%s' target='%s' style='%s' class='%s'>%s</a>" % (url, target, style, _class, title))
