from rest_framework.pagination import LimitOffsetPagination


class FastLimitOffsetPagination(LimitOffsetPagination):
    def paginate_queryset(self, queryset, request, view=None):
        self.limit = self.get_limit(request)
        if self.limit is None:
            return None

        self.count = None
        self.offset = self.get_offset(request)
        self.request = request

        return list(queryset[self.offset:self.offset + self.limit])
