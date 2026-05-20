from .selectors import stock_summary
from .serializers import serialize_stock_summary


def get_stock_summary():
    return serialize_stock_summary(stock_summary())

