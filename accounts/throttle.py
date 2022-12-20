from rest_framework.throttling import UserRateThrottle


class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'


class SustainedRateThrottle(UserRateThrottle):
    scope = 'sustained'


class BursAPIRateThrottle(UserRateThrottle):
    scope = 'burst_api'


class SustainedAPIRateThrottle(UserRateThrottle):
    scope = 'sustained_api'
