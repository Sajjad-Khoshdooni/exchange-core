from rest_framework.throttling import UserRateThrottle


class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'


class SustainedRateThrottle(UserRateThrottle):
    scope = 'sustained'


class BursApiRateThrottle(UserRateThrottle):
    scope = 'burst_api'


class SustaineApiRatethrottle(UserRateThrottle):
    scope = 'sustained_api'
