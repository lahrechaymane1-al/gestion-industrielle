from .selectors import apply_filters, base_queryset
from .serializers import serialize_production


def list_serialized(params):
    queryset = apply_filters(base_queryset(), params)
    return queryset, [serialize_production(item) for item in queryset]

