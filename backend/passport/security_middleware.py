import secrets
from urllib.parse import urlsplit

from django.conf import settings


def _payment_form_origin():
    """Return the configured eSewa origin as a CSP source expression."""
    payment_url = getattr(settings, 'ESEWA_PAYMENT_URL', '')
    parsed = urlsplit(payment_url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
        return None

    hostname = parsed.hostname
    if ':' in hostname:
        hostname = f'[{hostname}]'
    port = f':{parsed.port}' if parsed.port else ''
    return f'{parsed.scheme}://{hostname}{port}'


class ContentSecurityPolicyMiddleware:
    """Attach a per-response nonce and a restrictive browser content policy."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(18)
        response = self.get_response(request)
        if 'Content-Security-Policy' not in response:
            nonce = request.csp_nonce
            form_sources = ["'self'"]
            payment_origin = _payment_form_origin()
            if payment_origin:
                form_sources.append(payment_origin)
            response['Content-Security-Policy'] = '; '.join([
                "default-src 'self'",
                f"script-src 'self' 'nonce-{nonce}'",
                # Existing templates still use declarative click handlers.
                # Script blocks remain nonce-protected while those attributes
                # are migrated incrementally to addEventListener.
                "script-src-attr 'unsafe-inline'",
                f"style-src-elem 'self' 'nonce-{nonce}' https://fonts.googleapis.com",
                "style-src-attr 'unsafe-inline'",
                "font-src 'self' https://fonts.gstatic.com data:",
                "img-src 'self' data: blob:",
                "connect-src 'self'",
                "object-src 'none'",
                "base-uri 'self'",
                f"form-action {' '.join(form_sources)}",
                "frame-ancestors 'none'",
            ])
        return response


def csp_nonce(request):
    return {'csp_nonce': getattr(request, 'csp_nonce', '')}
