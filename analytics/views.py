from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, F, Value
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render
from openpyxl import Workbook

from accounts.models import TrafficSource


@login_required
def request_source_analytics(request):
    correct_url = settings.HOST_URL + '/analytics/marketing/reports/download/'
    context = {
        'redirect_url': correct_url
    }
    return render(request, 'datetime_form.html', context)


@login_required
def get_source_analytics(request):
    start_date_str = request.GET.get('start_date', None)
    end_date_str = request.GET.get('end_date', None)

    if start_date_str and end_date_str:

        start_datetime = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M').astimezone()
        end_datetime = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M').astimezone()

        if start_datetime < end_datetime - timedelta(days=30):
            return HttpResponseBadRequest('Report time filter threshold must be less than 30 days')

        qs1, qs2 = None, None

        if request.user.has_perm('accounts.has_marketing_adivery_reports'):
            qs1 = TrafficSource.objects.filter(
                created__range=[start_datetime, end_datetime],
                utm_source='yektanet',
                utm_medium='mobile'
            )
        if request.user.has_perm('accounts.has_marketing_mediaad_reports'):
            qs2 = TrafficSource.objects.filter(
                created__range=[start_datetime, end_datetime],
                utm_source='mediaad'
            )
        if not request.user.has_perm('accounts.has_marketing_adivery_reports') and not request.user.has_perm('accounts.has_marketing_mediaad_reports'):
            return HttpResponseForbidden('You do not have permission to view this content')

        # generate Excel workbook from queryset
        if qs1 is None and qs1 is None:
            return HttpResponseBadRequest('There is no data in this period')
        elif qs1 is None:
            result_queryset = qs2
        elif qs2 is None:
            result_queryset = qs1
        else:
            result_queryset = qs1.union(qs2)

        workbook = queryset_to_workbook(result_queryset)

        # create a response object
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=reports.xlsx'

        # write workbook to response
        workbook.save(response)

        return response

    return HttpResponseBadRequest('Invalid data')


def queryset_to_workbook(queryset, sheet_name='Sheet1'):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name

    headers = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'users', 'depositors']

    # write headers
    for col_num, header in enumerate(headers, 1):
        cell = sheet.cell(row=1, column=col_num)
        cell.value = header

    groups = queryset.values('utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term')\
        .annotate(
        user_count=Count('user__id', distinct=True),
        depositor_count=Count('user__id', distinct=True,
                              filter=Q(user__first_fiat_deposit_date__lte=F('user__date_joined') + Value(timedelta(days=1))) |
                                     Q(user__first_crypto_deposit_date__lte=F('user__date_joined') + Value(timedelta(days=1))))
    ).values_list('utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'user_count', 'depositor_count')

    # write data
    for row_num, row in enumerate(groups, 1):
        for col_num, field_name in enumerate(headers, 1):
            cell = sheet.cell(row=row_num+1, column=col_num)
            cell.value = row[col_num-1]

    return workbook
