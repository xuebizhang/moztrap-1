"""
Account-related views.

"""
from functools import partial

from django.conf import settings
from django.core.urlresolvers import reverse, resolve
from django.http import Http404
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_POST

from django.contrib.auth import REDIRECT_FIELD_NAME, views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from django_browserid.views import Verify as BaseVerify
from ratelimit.decorators import ratelimit
from registration.backends.default import views as registration_views
from session_csrf import anonymous_csrf

from moztrap import model
from . import forms



class Verify(BaseVerify):
    """BrowserID verification view."""
    def login_failure(self):
        """Handle a failed login."""
        messages.error(
            self.request,
            "Unable to sign in with that email address; "
            "have you registered an account?"
            )
        return redirect(
            "{0}?{1}={2}".format(
                settings.LOGIN_URL,
                REDIRECT_FIELD_NAME,
                self.request.REQUEST.get(REDIRECT_FIELD_NAME, "/"),
                )
            )


@anonymous_csrf
@ratelimit(field="username", method="POST", rate="5/m")
def login(request):
    # only allow ``next`` redirects to locations within moztrap.
    if "next" in request.GET:
        try:
            resolve(request.GET["next"])
        except Http404:
            q = request.GET.copy()
            q.update({"next": "/"})
            request.GET = q
    kwargs = {
        "template_name": "users/login.html",
        "authentication_form": forms.CaptchaAuthenticationForm,
        }
    if settings.USE_BROWSERID:
        kwargs["template_name"] = "users/browserid_login.html"
    # the contrib.auth login view doesn't pass request into the bound form,
    # but CaptchaAuthenticationForm needs it, so we ensure it's passed in
    if request.method == "POST":
        kwargs["authentication_form"] = partial(
            kwargs["authentication_form"], request)
    return auth_views.login(request, **kwargs)



@require_POST
def logout(request):
    return auth_views.logout_then_login(request)



def password_change(request):
    response = auth_views.password_change(
        request,
        template_name="users/password_change_form.html",
        password_change_form=forms.ChangePasswordForm,
        post_change_redirect=reverse("home")
        )

    if response.status_code == 302:
        messages.success(request, "Password changed.")

    return response



@anonymous_csrf
def password_reset(request):
    response = auth_views.password_reset(
        request,
        password_reset_form=forms.PasswordResetForm,
        template_name="users/password_reset_form.html",
        email_template_name="registration/password_reset_email.txt",
        subject_template_name="registration/password_reset_subject.txt",
        post_reset_redirect=reverse("home")
        )

    if response.status_code == 302:
        messages.success(
            request,
            u"Password reset email sent; check your email."
            u"If you don't receive an email, verify that you are entering the "
            u"email address you signed up with, and try again."
            )

    return response



@anonymous_csrf
def password_reset_confirm(request, uidb64, token):
    response = auth_views.password_reset_confirm(
        request,
        uidb64=uidb64,
        token=token,
        template_name="users/password_reset_confirm.html",
        set_password_form=forms.SetPasswordForm,
        post_reset_redirect=reverse("home")
        )

    if response.status_code == 302:
        messages.success(request, "Password changed.")

    return response


class ActivationView(registration_views.ActivationView):

    template_name = "users/activate.html"

    def activate(self, request, activation_key):
        activated_user = super(ActivationView, self).activate(
            request, activation_key
        )
        messages.success(request, "Account activated; now you can login.")
        return activated_user

    def get_success_url(self, request, user):
        return reverse("home")


class RegistrationView(registration_views.RegistrationView):

    form_class = forms.RegistrationForm
    template_name = "users/registration_form.html"

    def register(self, request, **cleaned_data):
        new_user = super(RegistrationView, self).register(
            request, **cleaned_data
        )
        messages.success(
            request, "Check your email for an account activation link.")
        return new_user

    def get_success_url(self, request, user):
        return reverse("home")


@login_required
def set_username(request):
    # only allow next redirects to places within moztrap.
    next = request.REQUEST.get("next", "/")
    try:
        resolve(next)
    except Http404:
        next = "/"

    if request.method == "POST":
        form = forms.SetUsernameForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect(next)
    else:
        form = forms.SetUsernameForm(instance=request.user)

    return render(
        request, "users/set_username_form.html", {"form": form, "next": next})



@require_POST
@login_required
def create_apikey(request, user_id):
    """Generate an API key for the given user; redirect to their edit page."""
    user = get_object_or_404(model.User, pk=user_id)
    model.ApiKey.generate(owner=user, user=request.user)

    return redirect("manage_user_edit", user_id=user_id)
