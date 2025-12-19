from django.urls import path
from .views import EmailSearchView

urlpatterns = [
    path("emails/", EmailSearchView.as_view(), name="email-search"),
]
