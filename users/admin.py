from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ['email', 'username', 'is_staff', 'num_movies_rated', 'num_movies_reviewed',]

admin.site.register(CustomUser, CustomUserAdmin)

# by default, admin is tightly coupled to the default User model, so above we extend the
# existing UserAdmin class to use our new CustomUser model.

