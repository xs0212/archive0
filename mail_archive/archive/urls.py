from django.urls import path
from .views import ArchiveIngestView, EmailDetailView, EmailVerifyView, ExportJobView

urlpatterns = [
    path("ingest/", ArchiveIngestView.as_view(), name="archive-ingest"),
    path("emails/<int:email_id>/", EmailDetailView.as_view(), name="email-detail"),
    path("emails/<int:email_id>/verify/", EmailVerifyView.as_view(), name="email-verify"),
    path("exports/", ExportJobView.as_view(), name="export-job"),
]
