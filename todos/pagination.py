from rest_framework.pagination import PageNumberPagination


class TodoPagination(PageNumberPagination):
    page_size = 20
    page_query_param = "page"
    page_size_query_param = "limit"
    max_page_size = 500


class DefaultPagination(PageNumberPagination):
    page_size = 25
    page_query_param = "page"
    page_size_query_param = "limit"
    max_page_size = 200
