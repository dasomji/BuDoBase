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
        react_page_request = (
            request.method == "GET"
            or (
                request.method == "POST"
                and request.path in {"/login/", "/register/"}
            )
        )
        should_render_react = (
            react_page_request
            and response.status_code == 200
            and content_type.startswith("text/html")
            and not request.path.startswith(self.excluded_prefixes)
            and "attachment" not in response.get("Content-Disposition", "")
        )
        if should_render_react:
            get_token(request)
            response.content = render_to_string(
                "react_app.html",
                {
                    "request_path": request.get_full_path(),
                },
                request=request,
            ).encode(response.charset)
            response["Content-Length"] = len(response.content)
        return response
