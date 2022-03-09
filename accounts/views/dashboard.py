from django.db.models import Q
from django.shortcuts import render
from accounts.models.user import User
from financial.models.withdraw_request import FiatWithdrawRequest
def dashboard(request):
    if request.method == 'GET':
        user = User.objects.all()
        user_count = user.count()
        user_pendin_or_reject_level_2_verification_count = user.filter(
            (Q(verify_status='pending') | Q(verify_status='rejected'))
        ).filter(level=1).count()
        user_pendin_or_reject_level_3_verification_count = user.filter(
            (Q(verify_status='pending') | Q(verify_status='reject'))
        ).filter(level=2).count()
        withdraw_request_pendeng_or_reject_count = FiatWithdrawRequest.objects.filter(
            status='pending',
        ).count()

        contex = {'user_count':user_count,
                  'user_pendin_or_reject_level_2_verification_count': user_pendin_or_reject_level_2_verification_count,
                  'user_pendin_or_reject_level_3_verification_count': user_pendin_or_reject_level_3_verification_count,
                  'withdraw_request_pendeng_or_reject_count': withdraw_request_pendeng_or_reject_count,
                  }
        return render(request, 'accounts/board.html',contex)
