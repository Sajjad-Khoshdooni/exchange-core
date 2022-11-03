from django.urls import path
from experiment.views import *

urlpatterns = [
    path('<int:token>', deposit_experiment_view),
]
