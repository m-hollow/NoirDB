from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):

    class Meta(UserCreationForm):
        model = CustomUser
        fields = ('username', 'email',)


class CustomUserChangeForm(UserChangeForm):

    class Meta:
        model = CustomUser
        fields = ('username', 'email',)


# the purpose of the above is to override / augment the default forms so they will
# also include our custom fields. The use of the Meta class
# allows us to make sure the new custom model includes all the standard / default
# fields the original class had, as well. we aren't actually using much or any custom stuff,
# so this looks minimal, but the idea is that if we have a custom user model, then we also
# need to define a custom user creation form and change form.