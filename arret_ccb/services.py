from .selectors import arret_summary
from .serializers import serialize_arret_summary


def get_arret_summary():
    return serialize_arret_summary(arret_summary())

