from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.models import NewsFeed
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from utils.paginations import EndlessPagination


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = EndlessPagination

    def get_queryset(self):
        queryset = NewsFeed.objects.filter(user=self.request.user)
        return self.paginate_queryset(queryset)

    def list(self, request):
        serializer = NewsFeedSerializer(
            self.get_queryset(),
            context={'request': request},
            many=True,
        )
        return self.get_paginated_response(serializer.data)
