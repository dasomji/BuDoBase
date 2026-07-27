from django.forms import BaseForm, BaseFormSet
from django.shortcuts import render


def _form_errors(value):
    if isinstance(value, BaseForm):
        return [
            str(error)
            for field_errors in value.errors.values()
            for error in field_errors
        ]
    if isinstance(value, BaseFormSet):
        return [
            *[str(error) for error in value.non_form_errors()],
            *[
                error
                for form in value.forms
                for error in _form_errors(form)
            ],
        ]
    return []


def context_form_errors(context):
    return [
        error
        for value in (context or {}).values()
        for error in _form_errors(value)
    ]


def render_react_page(request, context=None, *, status=None):
    shell_context = {
        **(context or {}),
        "request_path": request.get_full_path(),
    }
    response = render(
        request,
        "react_app.html",
        shell_context,
        status=status,
    )
    response.form_errors = context_form_errors(shell_context)
    return response


class ReactPageTemplateMixin:
    template_name = "react_app.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["request_path"] = self.request.get_full_path()
        return context

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        response.form_errors = context_form_errors(context)
        return response
