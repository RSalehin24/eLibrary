from django.http import HttpResponseBase


def protect_private_response(response: HttpResponseBase) -> HttpResponseBase:
    response["Cache-Control"] = "private, no-store"
    response["X-Robots-Tag"] = "noindex"
    return response
