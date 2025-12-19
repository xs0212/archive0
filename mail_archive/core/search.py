from elasticsearch import Elasticsearch
from django.conf import settings


def get_client() -> Elasticsearch:
    return Elasticsearch(settings.ELASTICSEARCH["HOSTS"], timeout=5)
