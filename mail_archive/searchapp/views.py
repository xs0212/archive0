from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from archive.models import ArchivedEmail
from accounts.access import AccessService
from audit.services import AuditService
from core.permissions import RBACPermission
from core.search import get_client
from .serializers import SearchRequestSerializer


class EmailSearchView(APIView):
    permission_classes = [RBACPermission]
    required_permission = "EMAIL_SEARCH"
    require_mfa = True

    def post(self, request):
        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        client = get_client()
        tags = AccessService.resolve_tags(request.user, data)
        must = []
        filters = [
            {"terms": {"access_tags": tags}},
            {"range": {"received_at": {"gte": data["time_start"].isoformat(), "lte": data["time_end"].isoformat()}}},
        ]
        if departments := data.get("departments"):
            filters.append({"terms": {"department_path": departments}})
        if participants := data.get("participants"):
            must.append({"terms": {"participants": participants}})
        if subject := data.get("subject"):
            must.append({"match": {"subject": {"query": subject, "fuzziness": "AUTO" if data["fuzzy"] else 0}}})
        if keywords := data.get("keywords"):
            must.append(
                {
                    "multi_match": {
                        "query": keywords,
                        "fields": ["body_text", "body_html", "attachments.filename"],
                        "fuzziness": "AUTO" if data["fuzzy"] else 0,
                    }
                }
            )
        query = {"bool": {"filter": filters, "must": must or [{"match_all": {}}]}}
        resp = client.search(
            index=settings.ELASTICSEARCH["INDEX"],
            query=query,
            from_=(data["page"] - 1) * data["size"],
            size=data["size"],
        )
        ids = [int(hit["_id"]) for hit in resp["hits"]["hits"]]
        emails = ArchivedEmail.objects.filter(id__in=ids)
        email_map = {email.id: email for email in emails}
        ordered = [email_map.get(eid) for eid in ids if email_map.get(eid)]
        results = [
            {
                "id": email.id,
                "subject": email.subject,
                "mailbox": email.mailbox.address,
                "received_at": email.received_at,
                "sha256": email.sha256,
            }
            for email in ordered
        ]
        AuditService.append(request.user, "EMAIL_SEARCH", data, result_count=resp["hits"]["total"]["value"])
        return Response({"results": results, "total": resp["hits"]["total"]["value"]})
