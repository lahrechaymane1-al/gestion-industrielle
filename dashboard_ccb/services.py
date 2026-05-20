from .selectors import dashboard_metrics
from .serializers import serialize_dashboard_metrics


def get_dashboard_metrics():
    return serialize_dashboard_metrics(dashboard_metrics())

