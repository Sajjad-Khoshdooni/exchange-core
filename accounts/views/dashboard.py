from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.shortcuts import render
from decouple import config

from accounts.models.user import User
from financial.models.withdraw_request import FiatWithdrawRequest
from ledger.models import Transfer


@staff_member_required
def dashboard(request):
    if request.method == 'GET':
        users = User.objects.all()
        user_count = users.count()

        pending_or_reject_level_2_users = users.filter(
            Q(verify_status=User.PENDING) | Q(verify_status=User.REJECTED),
            level=User.LEVEL1,
            archived=False
        ).count()

        pending_level_3_users = users.filter(
            verify_status=User.PENDING,
            level=User.LEVEL2,
            archived=False
        ).count()

        init_withdraw_requests = FiatWithdrawRequest.objects.filter(
            status=FiatWithdrawRequest.INIT,
        ).count()

        process_withdraw_requests = FiatWithdrawRequest.objects.filter(
            status=FiatWithdrawRequest.PROCESSING,
        ).count()

        crypto_withdraw_count = Transfer.objects.filter(deposit=False, status=Transfer.INIT).count()

        context = {
            'user_count': user_count,
            'pending_or_reject_level_2_users': pending_or_reject_level_2_users,
            'pending_level_3_users': pending_level_3_users,
            'init_withdraw_requests': init_withdraw_requests,
            'process_withdraw_requests': process_withdraw_requests,
            'archived_users': users.filter(archived=True).count(),
            'shahkar_rejected': users.filter(level=User.LEVEL2, national_code_phone_verified=False).count(),
            'brand': settings.BRAND,
            'crypto_withdraw_count': crypto_withdraw_count,
        }

        return render(request, 'accounts/dashboard.html', context)
