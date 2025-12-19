from django.urls import path
from .views import CurrentUserView, LoginView, MfaEnrollView, MfaVerifyView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("me/", CurrentUserView.as_view(), name="me"),
    path("mfa/enroll/", MfaEnrollView.as_view(), name="mfa-enroll"),
    path("mfa/verify/", MfaVerifyView.as_view(), name="mfa-verify"),
]
