from django import forms
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import FormView

from accounts.models import User
from accounts.verifiers.finotech import ServerError
from accounts.verifiers.jibit import JibitRequester


class ShahkarForm(forms.Form):
    phone = forms.CharField(label='phone')
    national_code = forms.CharField(label='national code')

    def clean_national_code(self):
        national_code = self.cleaned_data['national_code']

        if not User.objects.filter(national_code=national_code):
            raise ValidationError("invalid national_code")

        return national_code


class ShahkarCheckView(FormView):
    template_name = 'accounts/shahkar.html'
    form_class = ShahkarForm
    success_url = reverse_lazy('shahkar_check')

    def form_valid(self, form):
        national_code = form.cleaned_data['national_code']
        phone = form.cleaned_data['phone']

        user = User.objects.filter(national_code=national_code).order_by('id').last()
        requester = JibitRequester(user)
        try:
            matched = requester.matching(phone_number=phone, national_code=national_code)
        except (TimeoutError, ServerError):
            return HttpResponse("Jibit error")

        return HttpResponse("Matched: %s" % matched)
