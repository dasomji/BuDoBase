from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from budo_app.models import Profil


DUPLICATE_EMAIL_ERROR = "Diese E-Mail-Adresse wird bereits verwendet."
EMAIL_UNIQUE_INDEX_NAME = "auth_user_email_ci_unique"


def normalize_email(email):
    return email.strip().lower()


def email_is_already_used(email, *, exclude_user_id=None):
    users = User.objects.filter(email__iexact=email)
    if exclude_user_id is not None:
        users = users.exclude(pk=exclude_user_id)
    return users.exists()


def is_email_unique_integrity_error(error):
    cause = error.__cause__
    constraint_name = getattr(getattr(cause, "diag", None), "constraint_name", None)
    return (
        constraint_name == EMAIL_UNIQUE_INDEX_NAME
        or EMAIL_UNIQUE_INDEX_NAME in str(error)
    )


class LoginForm(forms.Form):
    username = forms.CharField(max_length=65)
    password = forms.CharField(max_length=65, widget=forms.PasswordInput)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    def clean_email(self):
        email = normalize_email(self.cleaned_data["email"])
        if email_is_already_used(email):
            raise forms.ValidationError(DUPLICATE_EMAIL_ERROR)
        return email

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class ProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True, label="E-Mail")

    class Meta:
        model = Profil
        fields = [
            "rufname",
            "email",
            "allergien",
            "coffee",
            "essen",
            "telefonnummer",
            "budo_family",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["email"].initial = self.instance.user.email

    def clean_email(self):
        email = normalize_email(self.cleaned_data["email"])
        user_id = self.instance.user_id if self.instance.pk else None
        if email_is_already_used(email, exclude_user_id=user_id):
            raise forms.ValidationError(DUPLICATE_EMAIL_ERROR)
        return email

    def save(self, commit=True):
        if not commit:
            return super().save(commit=False)

        with transaction.atomic():
            profile = super().save(commit=True)
            user = profile.user
            email = self.cleaned_data["email"]
            if user.email != email:
                user.email = email
                user.save(update_fields=["email"])
        return profile
