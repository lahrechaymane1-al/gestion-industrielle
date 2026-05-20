from django.core.paginator import Paginator

from .selectors import apply_filters, base_queryset
from .serializers import serialize_effectif


def list_paginated(params):
    queryset = apply_filters(base_queryset(), params)
    page = int(params.get("page") or 1)
    per_page = min(int(params.get("per_page") or 15), 100)
    page_obj = Paginator(queryset, per_page).get_page(page)
    return page_obj, [serialize_effectif(item) for item in page_obj]

