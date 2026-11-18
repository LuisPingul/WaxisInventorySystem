from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Profile

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control form-control-lg", "placeholder": "Username"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control form-control-lg", "placeholder": "Password"})
    )
    remember_me = forms.BooleanField(required=False, initial=True)

class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Temporary password"})
    )
    role = forms.ChoiceField(
        choices=Profile.Role.choices,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        if actor and getattr(getattr(actor, "profile", None), "role", None) == Profile.Role.OWNER:
            self.fields["role"].choices = [
                (Profile.Role.MANAGER, "Manager"),
                (Profile.Role.CREW, "Crew"),
            ]

    def clean_role(self):
        selected_role = self.cleaned_data.get("role")
        actor_role = getattr(getattr(self.actor, "profile", None), "role", None)
        if actor_role == Profile.Role.OWNER and selected_role not in {
            Profile.Role.MANAGER,
            Profile.Role.CREW,
        }:
            raise forms.ValidationError("Owners may only provision Manager or Crew accounts.")
        return selected_role

    def clean_password(self):
        password = self.cleaned_data.get("password", "")
        user_stub = User(
            username=self.cleaned_data.get("username", ""),
            first_name=self.cleaned_data.get("first_name", ""),
            last_name=self.cleaned_data.get("last_name", ""),
            email=self.cleaned_data.get("email", ""),
        )
        validate_password(password, user=user_stub)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        selected_role = self.cleaned_data["role"]

        # Developer/Owner are the two highest-level accounts.
        # Owner can create Manager/Crew; Developer can create any role.
        if selected_role in {Profile.Role.DEVELOPER, Profile.Role.OWNER}:
            user.is_staff = True
            user.is_superuser = True

        if commit:
            user.save()
            Profile.objects.update_or_create(
                user=user,
                defaults={"role": selected_role},
            )
        return user