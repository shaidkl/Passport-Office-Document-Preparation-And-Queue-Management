from rest_framework.throttling import SimpleRateThrottle


class PublicTrackingThrottle(SimpleRateThrottle):
    """Limit anonymous tracking attempts to slow reference enumeration."""

    scope = 'public_tracking'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }
