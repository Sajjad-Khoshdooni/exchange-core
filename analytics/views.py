from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render
from openpyxl import Workbook

from accounts.models import TrafficSource, User


@login_required
def request_source_analytics(request):
    my_url = settings.HOST_URL + '/api/v1/analytics/traffic/'
    context = {
        'redirect_url': my_url
    }
    return render(request, 'datetime_form.html', context)


@login_required
def get_source_analytics(request):
    start_date_str = request.GET.get('start_date', None)
    end_date_str = request.GET.get('end_date', None)

    if start_date_str and end_date_str:

        start_datetime = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
        end_datetime = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')

        if request.user.has_perm('accounts.read_yektanet_mobile'):
            queryset = TrafficSource.objects.filter(
                created__range=[start_datetime, end_datetime],
                utm_source='yektanet',
                utm_medium='mobile'
            )
            print(queryset)
        elif request.user.has_perm('accounts.read_mediaad'):
            queryset = TrafficSource.objects.filter(
                created__range=[start_datetime, end_datetime],
                utm_source='mediaad'
            )
        else:
            return HttpResponseForbidden('You do not have permission to view this content')


        # generate Excel workbook from queryset
        workbook = queryset_to_workbook(queryset)

        # create a response object
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=my_file.xlsx'

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

    groups = queryset.values('utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term')
    # write data
    for row_num, row in enumerate(groups, 1):
        for col_num, field_name in enumerate(headers, 1):
            cell = sheet.cell(row=row_num+1, column=col_num)
            cell.value = row.get(field_name)
        _list = queryset.filter(
            utm_source=row.get('utm_source'),
            utm_medium=row.get('utm_medium'),
            utm_campaign=row.get('utm_campaign'),
            utm_content=row.get('utm_content'),
            utm_term=row.get('utm_term')
        )
        cell = sheet.cell(row=row_num + 1, column=6)
        cell.value = len(_list)

        cell = sheet.cell(row=row_num + 1, column=7)
        cell.value = len(User.objects.filter(id__in=_list.values_list('user__id', flat=True)).exclude(
            Q(first_fiat_deposit_date__isnull=True) |
            Q(first_crypto_deposit_date__isnull=True)
        ))
    return workbook
