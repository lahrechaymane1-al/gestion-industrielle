from .selectors import apply_filters, base_queryset
from .serializers import serialize_arret


def list_serialized(params):
    queryset = apply_filters(base_queryset(), params)
    return queryset, [serialize_arret(item) for item in queryset]

