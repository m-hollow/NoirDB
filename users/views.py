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

        # this generic class-based view has been modified so that the user gets automatically logged in after
        # they create their new account. it essentially combines the behavior of the function-based view in
        # learning-logs with the class-based view in learndjango (which did NOT log user in automatically).
        # Note: there is more than one way to do this! See your text file "doing more work in form_valid before return"
        # to see another approach to writing form_valid with additional operations.


class CloseAccount(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = get_user_model()
    template_name = 'registration/close_account.html'
    fields = []
    query_pk_and_slug = True

    login_url = 'films:index'

    success_url = reverse_lazy('users:close_success')

    def test_func(self):
        obj = self.get_object()
        return obj == self.request.user  # the obj itself is a user object, so we don't do '.user' here like we did on Review

    # the form instance corresponds to the model set above, which is the user model, and this UpdateView is working on the current instance
    # of that model
    def form_valid(self, form):
        form.instance.is_active = False

        return super().form_valid(form)

    # the alternative is to not make this a part of an UpdateView nor an (invisible) From at all,
    # and simply modify this value in a DetailView with this code (but what method of DetailView would it go in??):
        # user = get_user_model()    # actually, WRONG: this gets the user Class itself, not the user instance. 

        # user.is_active = False
        # user.save()

    # now, it's true that this is modifying contents of the db and saving it, so you'd think an UpdateView + Form is
    # the 'right' way to do it, but remember that 1. there is no -actual- user form input going on here, we are
    # bypassing all that; and 2. the example of 'performing extra work' in the class-based views documentation
    # has them modfying the 'last_accessed' field of the model and saving it, with no editing view / form involved
    # in the process. you only *need* a Post request (via a form) if you -need literal user input of whatever kind-,
    # whereas you are just taking the actual click of a button as the input itself. it's possible that all of your
    # 'invisible forms' that modify the db could actually just be detailviews with NO forms and code logic that 
    # updates the db accordingly, since you are not literally taking in user input into a form field at any point
    # within those processes! you would just set the field to the value you want, and then call save on the object.
    # conceivably, you could write this as a method of the model itself, and then all the view would need to do is call
    # that method on the object instance. only question that remains is: if it's a class-based view such as DetailView,
    # where inside the view's body does this call occur? you'd need to overrite an appropriate method: in the django chapter
    # referenced earlier in this paragraph ('built in class-based generic views') re: 'Performing Extra Work' uses the
    # 'get_object' method of DetailView, so that is probably your best bet.


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
