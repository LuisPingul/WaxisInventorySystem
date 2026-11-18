from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from audit.services import log_action
from config.security import invalidate_user_sessions

from .decorators import role_required
from .forms import UserCreateForm
from .models import Profile


def login_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            if not user.is_active:
                messages.error(request, "This account is inactive.")
                return render(request, "accounts/login.html")

            login(request, user)
            return redirect_by_role(user)

        messages.error(request, "Invalid username or password.")

    return render(request, "accounts/login.html")


def redirect_by_role(user):
    try:
        role = user.profile.role
    except Profile.DoesNotExist:
        return redirect("accounts:login")

    if role in {
        Profile.Role.DEVELOPER,
        Profile.Role.OWNER,
        Profile.Role.MANAGER,
        Profile.Role.CREW,
    }:
        return redirect("dashboard:home")

    return redirect("accounts:login")


@login_required
@require_POST
def logout_view(request):
    # Consume and clear any unread messages from previous authenticated actions
    # to ensure internal business/inventory alerts never leak to the public login screen.
    list(messages.get_messages(request))
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("accounts:login")


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER)
def users(request):
    all_users = Profile.objects.select_related("user").order_by("user__username")

    return render(
        request,
        "accounts/users.html",
        {"users": [profile.user for profile in all_users]},
    )


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER)
def create_user(request):
    form = UserCreateForm(request.POST or None, actor=request.user)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        log_action(
            request.user,
            "CREATE",
            "Accounts",
            user.pk,
            f"User '{user.username}' created with role {user.profile.role}.",
        )
        messages.success(
            request,
            f"User '{user.username}' was created successfully.",
        )
        return redirect("accounts:users")

    return render(request, "accounts/user_form.html", {"form": form})


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER)
@require_POST
def toggle_user(request, user_id):
    from django.contrib.auth.models import User
    from django.shortcuts import get_object_or_404

    user = get_object_or_404(User, pk=user_id)

    if user == request.user:
        messages.error(request, "You cannot disable your own account.")
        return redirect("accounts:users")

    # VibeSec Vertical Access Control: Owners cannot disable Developer accounts
    actor_role = getattr(getattr(request.user, "profile", None), "role", None)
    target_role = getattr(getattr(user, "profile", None), "role", None)
    if actor_role == Profile.Role.OWNER and target_role in {Profile.Role.DEVELOPER, Profile.Role.OWNER}:
        messages.error(request, "Insufficient permissions to modify a Developer or Owner account.")
        return render(request, "403.html", status=403)

    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])

    # VibeSec Account Lifecycle: Invalidate all active sessions when deactivated
    if not user.is_active:
        invalidate_user_sessions(user.pk)

    status = "activated" if user.is_active else "disabled"
    log_action(
        request.user,
        "TOGGLE",
        "Accounts",
        user.pk,
        f"User '{user.username}' {status}.",
    )
    messages.success(request, f"User '{user.username}' has been {status}.")

    return redirect("accounts:users")
