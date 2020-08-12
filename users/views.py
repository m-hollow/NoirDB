# these were all used just for the old function-based register view function:
#from django.shortcuts import render, redirect
#from django.contrib.auth import login
#from django.contrib.auth.forms import UserCreationForm

from django.urls import reverse, reverse_lazy
from django.shortcuts import redirect
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, CreateView, UpdateView

from .forms import CustomUserCreationForm

class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('films:index')
    template_name = 'registration/register.html'       # must use full path (registration/register.html)

    def form_valid(self, form):
        self.object = form.save()                   # saves the new user object (self.object is user object)
        login(self.request, self.object)            # logs in the new user
        return redirect(self.get_success_url())       # return success_url to redirect

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_name'] = 'Register Account'
        return context


class CloseAccount(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = get_user_model()
    template_name = 'registration/close_account.html'
    fields = []
    query_pk_and_slug = True

    login_url = 'films:index'

    success_url = reverse_lazy('close_success')

    def test_func(self):
        obj = self.get_object()
        return obj == self.request.user  # the obj itself is a user object, so we don't do '.user' here like we did on Review

    # the form instance corresponds to the model set above, which is the user model, and this UpdateView is working on the current instance
    # of that model
    def form_valid(self, form):
        form.instance.is_active = False

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_name'] = 'Close Account'
        return context


# simple page that announces success upon deactivating a user
class CloseSuccess(TemplateView):
    template_name = 'registration/close_success.html'



# old function-basd version:
# def register(request):
#     """Register a new user."""
#     if request.method != 'POST':
#         # Display blank registration form.
#         form = CustomUserCreationForm()
#     else:
#         # Process completed form.
#         form = CustomUserCreationForm(data=request.POST)

#         if form.is_valid():
#             new_user = form.save()
#             # Log the user in and then redirect to the homepae.
#             login(request, new_user)
#             return redirect('films:index')

#     # Display a blank or invalid form.
#     context = {'form': form}
#     return render(request, 'registration/register.html', context)
