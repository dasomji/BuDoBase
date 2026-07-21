import re

from django.middleware.csrf import get_token
from django.template.loader import render_to_string


class ReactFrontendMiddleware:
    """Replace successful HTML page responses with the React application shell.

    Existing Django views remain the authorization and mutation boundary. Their
    GET handlers are still resolved first, so object-level 404s and login
    redirects retain the same behavior while page rendering moves to React.
    """

    excluded_prefixes = ("/admin/", "/api/", "/static/", "/media/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get("Content-Type", "")
        should_render_react = (
            request.method in {"GET", "POST"}
            and response.status_code == 200
            and content_type.startswith("text/html")
            and not request.path.startswith(self.excluded_prefixes)
            and "attachment" not in response.get("Content-Disposition", "")
        )
        if should_render_react:
            legacy_html = response.content.decode(response.charset)
            body_match = re.search(
                r"<body[^>]*>(?P<body>.*)</body>",
                legacy_html,
                flags=re.IGNORECASE | re.DOTALL,
            )
            legacy_body = body_match.group("body") if body_match else legacy_html
            legacy_body = re.sub(
                r"<script\b[^>]*>.*?</script>",
                "",
                legacy_body,
                flags=re.IGNORECASE | re.DOTALL,
            )
            get_token(request)
            response.content = render_to_string(
                "react_app.html",
                {
                    "request_path": request.get_full_path(),
                    "react_print_page": bool(re.fullmatch(
                        r"(?:/happy-cleaning/\d+/print/|/swp-einteilung-w[12]/?)",
                        request.path,
                    )),
                    "legacy_print_body": legacy_body,
                    "legacy_uses_google_font": "fonts.googleapis.com" in legacy_html,
                },
                request=request,
            ).encode(response.charset)
            response["Content-Length"] = len(response.content)
        return response
