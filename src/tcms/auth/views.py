# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib import auth
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from tcms.auth.forms import RegistrationForm
from tcms.auth.models import UserActivateKey
from tcms.core.views import prompt


@require_GET
def logout(request):
    """Logout method of account"""
    auth.logout(request)
    return redirect(request.GET.get("next", settings.LOGIN_URL))


@require_http_methods(["GET", "POST"])
def register(request, template_name="registration/registration_form.html"):
    """Register method of account"""

    request_data = request.GET or request.POST

    # Check that registration is allowed by backend config
    user_pwd_backend_config = settings.ENABLED_AUTH_BACKENDS.get("USERPWD")

    if user_pwd_backend_config is None or not user_pwd_backend_config.get("ALLOW_REGISTER"):
        return prompt.alert(
            request,
            "The backend is not allowed to register.",
            request_data.get("next", reverse("nitrate-index")),
        )

    if request.method == "POST":
        form = RegistrationForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            form.save()
            ak = form.set_active_key()

            # Send email to user if mail server is available.
            if form.cleaned_data["email"] and settings.EMAIL_HOST:
                form.send_confirm_mail(request=request, active_key=ak)

                msg = "Your account has been created, please check your mailbox for confirmation."
            else:
                msg = [
                    "<p>Your account has been created, but you need to contact "
                    "an administrator to active your account.</p>",
                ]
                # If can not send email, prompt to user.
                if settings.ADMINS:
                    msg.append("<p>Following is the admin list</p><ul>")
                    for name, email in settings.ADMINS:
                        msg.append(f'<li><a href="mailto:{email}">{name}</a></li>')
                    msg.append("</ul>")
                    msg = "".join(msg)

            return prompt.info(request, msg, request.POST.get("next", reverse("nitrate-index")))
    else:
        form = RegistrationForm()

    context_data = {
        "form": form,
    }
    return render(request, template_name, context=context_data)


@require_GET
def confirm(request, activation_key):
    """Confirm the user registration"""

    # Get the object
    try:
        ak = UserActivateKey.objects.select_related("user")
        ak = ak.get(activation_key=activation_key)
    except UserActivateKey.DoesNotExist:
        return prompt.info(
            request,
            "This key no longer exist in the database.",
            request.GET.get("next", reverse("nitrate-index")),
        )

    # All thing done, start to active the user and use the user login
    user = ak.user
    user.is_active = True
    user.save(update_fields=["is_active"])
    ak.delete()
    # login(request, user)

    # Response to web browser.
    return prompt.info(
        request,
        "Your account has been activated successfully, click next link to re-login.",
        request.GET.get("next", reverse("user-profile-redirect")),
    )


class LoginView(DjangoLoginView):
    """Custom Django admin LoginView to provide social auth backends info"""

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        social_auth_backends = settings.ENABLED_AUTH_BACKENDS.get("SOCIAL")
        if social_auth_backends is not None:
            data.update(
                {
                    "social_auth_backends": [
                        (
                            # URL
                            reverse("social:begin", args=[backend_info["backend"]]),
                            # Display label
                            backend_info["label"],
                            # title in A
                            backend_info["title"],
                        )
                        for backend_info in social_auth_backends
                    ]
                }
            )

        return data
