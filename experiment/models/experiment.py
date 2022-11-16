from django.db import models
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.html import format_html

from analytics.utils import produce_users_analytics
from experiment.models.variant import Variant
from experiment.models.variant_user import VariantUser


class Experiment(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=20)
    active = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return self.name

    @admin.display
    def variants_result(self):
        variant_list = Variant.objects.filter(experiment=self)
        html_url = '<table><tr><th>Parameters</th>'
        for variant in variant_list:
            html_url += format_html("<th>{}</th>", variant.name)
        html_url += '</tr>'

        user_analytics_list = [
            produce_users_analytics(VariantUser.objects.filter(variant=variant).values_list('user__id', flat=True))
            for variant in variant_list
        ]
        for key in user_analytics_list[0].keys():
            html_url += '<tr><td>{}</td>'.format(key)

            for user_analytics in user_analytics_list:
                html_url += format_html("<td>{}</td>", user_analytics.get(key))

            html_url += '</tr>'

        html_url += '</table>'

        return mark_safe(html_url)
