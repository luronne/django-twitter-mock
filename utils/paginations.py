from dateutil import parser
from rest_framework.pagination import BasePagination
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class FriendshipPagination(PageNumberPagination):
    # default page size
    page_size = 20
    # page_size_query_param to customize page size on different clients
    page_size_query_param = 'size'
    # maximum size allowed for clients
    max_page_size = 20

    def get_paginated_response(self, data):
        return Response({
            'total_results': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'page_number': self.page.number,
            'has_next_page': self.page.has_next(),
            'results': data,
        })


class EndlessPagination(BasePagination):
    page_size = 20
    has_next_page = False

    def __int__(self):
        super(EndlessPagination, self).__init__()

    def to_html(self):
        pass

    def paginate_ordered_list(self, reverse_ordered_list, request):
        if 'created_at__gt' in request.query_params:
            created_at__gt = parser.isoparse(request.query_params['created_at__gt'])
            objects = []
            for obj in reverse_ordered_list:
                if obj.created_at > created_at__gt:
                    objects.append(obj)
                else:
                    break
            self.has_next_page = False
            return objects

        index = 0
        if 'created_at__lt' in request.query_params:
            created_at__lt = parser.isoparse(request.query_params['created_at__lt'])
            for index, obj in enumerate(reverse_ordered_list):
                if obj.created_at < created_at__lt:
                    break
            else:
                reverse_ordered_list = []
        self.has_next_page = len(reverse_ordered_list) > index + self.page_size
        return reverse_ordered_list[index: index + self.page_size]

    def paginate_queryset(self, queryset, request, view=None):
        # check the type of the queryset
        if type(queryset) == list:
            return self.paginate_ordered_list(queryset, request)

        # refresh the page will load all latest posts
        if 'created_at__gt' in request.query_params:
            created_at__gt = request.query_params['created_at__gt']
            queryset = queryset.filter(created_at__gt=created_at__gt)
            self.has_next_page = False
            return queryset.order_by('-created_at')

        # reload the page for older posts
        if 'created_at__lt' in request.query_params:
            created_at__lt = request.query_params['created_at__lt']
            queryset = queryset.filter(created_at__lt=created_at__lt)

        # check if next page exists, to avoid empty load
        queryset = queryset.order_by('-created_at')[:self.page_size + 1]
        self.has_next_page = len(queryset) > self.page_size
        return queryset[:self.page_size]

    def get_paginated_response(self, data):
        return Response({
            'has_next_page': self.has_next_page,
            'results': data,
        })
