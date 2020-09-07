from itertools import chain
from operator import attrgetter
from random import sample, randint

from django.shortcuts import render, redirect
#from django.contrib.auth.decorators import login_required          # no longer used after switch to class-based views
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, JsonResponse
from django.urls import reverse, reverse_lazy
from django.core.mail import send_mail, BadHeaderError

from django.contrib.auth import get_user_model # this is here so user_detail view can set its model to user Model

from django.views.generic import (TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView)
from .models import (Person, Movie, Cast, Job, Crew, Review, UserMovieLink, MediaLink, DailyMovie)
from .forms import ReviewForm, ContactForm


class IndexPage(TemplateView):
    template_name = 'films/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        top_five = get_top_five()

        current_daily_record = DailyMovie.objects.get(active_movie=True)
        current_daily_movie = current_daily_record.movie

        if not current_daily_record.check_update_status():
            daily_movie = current_daily_movie         # 24 has not elapsed, keep the same movie
        else:
            active = True

            while active:
                random_num = randint(0, 580)
                new_choice = Movie.objects.all()[random_num]

                if new_choice.name == None:     # just a security check to avoid infinitely running while loop
                    daily_movie = current_daily_movie
                    active = False
                else:
                    if new_choice.name == current_daily_movie.name:  # you MUST check on a field, not compare the objects themselves; they will be different!
                        continue                                 # Model objects are not identical, even if its the same record!
                    else:
                        current_daily_record.active_movie = False
                        current_daily_record.save()

                        new_record = DailyMovie(movie=new_choice, active_movie=True, daily_count=current_daily_record.daily_count+1)
                        new_record.save()

                        daily_movie = new_choice
                        active = False


        daily_director = daily_movie.all_crew.get(crew__job__job_title='Director')
        daily_media_links = daily_movie.medialink_set.all()

        related_movies = daily_movie.get_related_movies()

        free_count = Movie.objects.filter(medialink__free=True).distinct().count() # movies can have more than one free link, distinct avoids counting duplicates

        context['free_count'] = free_count
        context['page_name'] = 'Welcome'
        context['daily_director'] = daily_director
        context['daily_movie'] = daily_movie
        context['daily_media_links'] = daily_media_links
        context['related_movies'] = related_movies
        context['top_five'] = top_five

        return context


class MovieList(ListView):
    #paginate_by = 30
    queryset = Movie.objects.order_by('name')
    template_name = 'films/all_movies.html'
    context_object_name = 'all_movies'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        alphabet = 'abcdefghijklmnopqrstuvwxyz'
        num_starts = ['5', '7', '9']

        # all_movies = context['all_movies']
        sorted_movies = {}
        numerics = []

        # create a key-value pair for each letter of alphabet, value is query result of movies starting with that letter
        for i in alphabet:
            sorted_movies[i] = Movie.objects.filter(display_name__istartswith=i)

        # get the movies that don't start with a letter
        for i in num_starts:
            results = Movie.objects.filter(display_name__istartswith=i)
            numerics.extend(results)

        context['sorted_movies'] = sorted_movies
        context['numerics'] = numerics
        context['page_name'] = 'All Movies'
        return context


class FreeMoviesList(ListView):
    paginate_by = 20
    template_name = 'films/free_movies.html'
    context_object_name = 'free_movies'
    count = 0

    def get_queryset(self):
        # get only the movies with a free link
        free_movies = Movie.objects.filter(medialink__free=True).distinct() # if a movie has more than one free medialink, it would show up twice without discint() here
        self.count = free_movies.count()

        return free_movies


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['free_count'] = self.count
        context['page_name'] = 'Free Movies'
        return context


class MovieDetail(DetailView):
    model = Movie
    template_name = 'films/movie.html'
    context_object_name = 'movie'
    query_pk_and_slug = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # grab the Person objects based on their Job Title, via Crew
        director = self.object.all_crew.get(crew__job__job_title='Director')
        camera = self.object.all_crew.get(crew__job__job_title='Cinematographer')

        try:
            composer = self.object.all_crew.get(crew__job__job_title='Composer')
        except Person.DoesNotExist: # prefix: name the model that you are attempting to retreive
            composer = ''

        # filter returns a list, so these will always be lists...
        producers = self.object.all_crew.filter(crew__job__job_title='Producer')
        writers = self.object.all_crew.filter(crew__job__job_title='Writer')

        crew_dict = {
            'director': director,
            'camera': camera,
            'composer': composer,
            'producers': producers,
            'writers': writers,
        }

        # the context does not actually include 'cast' objects; so to sort on 'starring role', you need to do
        # it here, in the view.

        # get all Person objects from this Movie's cast who are Starring Roles
        starring_cast = self.object.all_cast.filter(cast__starring_role=True).order_by('name')
        # get all Person objects from this Movie's cast who are not Starring Roles
        cast = self.object.all_cast.filter(cast__starring_role=False).order_by('name')

        starring_role_pairs = [] # store a Person object and role they played together in a list, nested in this list
        cast_role_pairs = [] 

        # get the role each person played from the intermediary table Cast, then store both (person and role) together in a list
        for person in starring_cast:
            role_played = person.cast_set.get(movie=self.object).role  # role is an attribute of the cast object returned by the query
            starring_role_pairs.append([person, role_played])

        # get the role each person played from the intermediary table Cast, then store both (person and role) together in a list
        for person in cast:
            role_played = person.cast_set.get(movie=self.object).role # grab role attribute from record instance returned by get()
            #role_played = self.object.cast_set.get(person=person).role
            cast_role_pairs.append([person, role_played])


        # the movie.based_on field is a CharField, but I want to break it down into smaller pieces, for better template formatting:
        if self.object.based_on != 'n/a':
            based_on_string = self.object.based_on
            based_on_list = based_on_string.split('By') # returns a list with strings for text and author
            based_on_list = [item.strip() for item in based_on_list]  # get rid of whitespace from the split()

            context['based_on_list'] = based_on_list  # note: if movie.based_on == 'n/a', the template context will not have this element;
                                                      # right now that's ok, because the template does a check on movie.based_on, not on the context...

        # get any reviews of the movie. the template will do the conditional check against None.
        movie_reviews = self.object.review_set.all().order_by('-date_added')

        # get any medialink records from MediaLink table; this is also a reverse connection
        # (MediaLink defines the FK relationship to Movie)
        media_links = self.object.medialink_set.all()

        if self.request.user.is_authenticated:

            # get user's movie review, if one exists:
            if Review.objects.filter(movie=self.object, user=self.request.user).exists():
                user_review = Review.objects.get(movie=self.object, user=self.request.user)

            else:
                user_review = None

            # get UserMovieLink (details of user+movie), if one exists:
            if UserMovieLink.objects.filter(movie=self.object, user=self.request.user).exists():
                user_movie_details = UserMovieLink.objects.get(movie=self.object, user=self.request.user)
            else:
                user_movie_details = None

            # important note: you MUST use filter, not get, when doing an 'exists' check.
            # if you use get, it will still raise a DoesNotExist error.

        # user not logged in, give user review and user movie details both values of None
        else:
            user_review = None
            user_movie_details = None

        # these are simply used as arguments passed in url template tags, captured by URLconf,
        # and the view called by that URL will use them for conditional branching about what to do
        # next
        action_dict = {
            'mark_seen': 'mark_seen',
            'unmark_seen': 'unmark_seen',
            'mark_favorite': 'mark_favorite',
            'unmark_favorite': 'unmark_favorite',
            'mark_watch_list': 'mark_watch_list',
            'unmark_watch_list': 'unmark_watch_list',
        }


        # build the complete context
        context['crew_dict'] = crew_dict
        context['starring_list'] = starring_role_pairs
        context['cast_list'] = cast_role_pairs
        context['reviews'] = movie_reviews
        context['media_links'] = media_links
        context['user_review'] = user_review       # value is Review object or None
        context['user_movie_details'] = user_movie_details  # value is UserMovieLink object or None
        context['actions'] = action_dict
        context['page_name'] = self.object.display_name

        return context


class PersonList(ListView):
    paginate_by = 30
    queryset = Person.objects.order_by('name')
    template_name = 'films/all_people.html' # this template doesn't exist yet !
    context_object_name = 'all_people'


class PersonDetail(DetailView):
    model = Person
    template_name = 'films/person.html'
    context_object_name = 'person'
    query_pk_and_slug = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # my additional context...

        # get all Movie objects from Person object, via related name moves_cast
        movies_as_actor = self.object.movies_cast.distinct().order_by('name')
        movie_role_pairs = []

        if movies_as_actor:
            for movie in movies_as_actor:
                role_played = self.object.cast_set.get(movie=movie).role # alternately, we could go through movie
                movie_role_pairs.append([movie, role_played])

        # get all Movie objects from Person object, via related name movies_crew

        # use .distinct() to avoid getting duplicate movie objects (some people have multiple crew credits on one movie)
        movies_as_crew = self.object.movies_crew.distinct().order_by('name') # why is this not working? template results are not alphabetical!
        movie_job_pairs = []

        if movies_as_crew:
            for movie in movies_as_crew:
                job_list = []
                # get crew objects, through Person object, via reverse manager crew_set, for current movie
                crew_credits = self.object.crew_set.filter(movie=movie)

                # we can use direct access from crew object to get the job object with .job
                for crew_ob in crew_credits:
                    job_list.append(crew_ob.job) # add job object to job_list

                movie_job_pairs.append([movie, job_list])

        context['movie_role_pairs'] = movie_role_pairs
        context['movie_job_pairs'] = movie_job_pairs
        context['page_name'] = self.object.name
        return context


class SearchResults(ListView):
    paginate_by = 20
    template_name = 'films/search_results.html'
    context_object_name = 'search_results'
    count = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['count'] = self.count or 0
        context['query'] = self.request.GET.get('q') # this is here purely so we can display it in the template

        movie_results = []
        people_results = []

        # Note: yes, you can access 'search_results' from the context object here, after the call to
        # super-- this works because get_queryset has already been called, and the result returned from it has been
        # given the name 'search_results' as defined in the attributes above these methods (context_object_name = ...)
        search_results = context['search_results']

        for result in search_results:
            if isinstance(result, Movie):
                movie_results.append(result)
            else:
                people_results.append(result)

        context['movie_results'] = movie_results
        context['people_results'] = people_results
        context['page_name'] = 'Search Results'

        return context

    def get_queryset(self):

        query = self.request.GET.get('q') # self is the instance of the class-based view, create per-use.

        movie_list = Movie.objects.filter(name__icontains=query).order_by('name')
        person_list = Person.objects.filter(name__icontains=query).order_by('name')

        total_list = sorted(chain(movie_list, person_list), key=attrgetter('name'))

        # Q: isn't it redundant to use both order_by() on the query and sorted() on the total list?

        self.count = len(total_list) # update the count so it can be displayed in results

        return total_list


def autocomplete_view(request):
    """Called by the jQueryUI autocomplete widget to use ajax for autocompletion in search field"""
    if 'term' in request.GET:
        qs_movies = Movie.objects.filter(display_name__icontains=request.GET.get('term'))
        qs_people = Person.objects.filter(name__icontains=request.GET.get('term'))

        total_package = []

        for movie in qs_movies:
            name = movie.display_name
            relative_url = movie.get_absolute_url()
            url = request.build_absolute_uri(relative_url)
            total_package.append({'label': name, 'url': url})

        for person in qs_people:
            name = person.name
            relative_url = person.get_absolute_url()
            url = request.build_absolute_uri(relative_url)
            total_package.append({'label': name, 'url': url})

        return JsonResponse(total_package, safe=False)

    # note that this function is not a typical view -- it does not render a new page; it exists only to 
    # return JSON data to the caller (jQuery UI autocomplete). 


class UserDetail(LoginRequiredMixin, DetailView): # I'm assuming this mixin works on DetailView as well as CreateView...
    model = get_user_model()
    template_name = 'films/user_detail.html'

    query_pk_and_slug = True

    login_url = 'login' # will be used by the LoginRequiredMixin if non-logged in user tries access

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        uml_seen = self.object.usermovielink_set.filter(seen=True).order_by('movie__name')
        uml_favs = self.object.usermovielink_set.filter(favorite=True).order_by('movie__name')
        uml_watch = self.object.usermovielink_set.filter(watch_list=True).order_by('movie__name')

        user_reviews = self.object.review_set.all().order_by('-date_added')  # note the '-' for descending order by date

        # this shows up twice throughout your views; how to refactor to one location, used by both views?
        action_dict = {
            'mark_seen': 'mark_seen',
            'unmark_seen': 'unmark_seen',
            'mark_favorite': 'mark_favorite',
            'unmark_favorite': 'unmark_favorite',
            'mark_watch_list': 'mark_watch_list',
            'unmark_watch_list': 'unmark_watch_list',
            }

        context['uml_seen'] = uml_seen
        context['uml_favs'] = uml_favs
        context['uml_watch'] = uml_watch

        context['user_reviews'] = user_reviews
        context['actions'] = action_dict
        context['page_name'] = 'User Details'

        return context


class WriteReview(LoginRequiredMixin, CreateView):

    # create view does NOT have a get_queryset method! that is for DetailView and ListView
    model = Review
    template_name = 'films/write_review.html'
    context_object_name = 'review'      # I think this is unnecessary, the template is for form display...

    form_class = ReviewForm

    login_url = 'login' # will be used by the LoginRequiredMixin if non-logged in user attempts access

    # NOTE: I'm not using success_url here because the Review model has a get_absolute_url method defined,
    # and the CreateView will use that automatically; if the Review model didn't have that method,
    # you would be required to add either success_url to attributes or add a method override for
    # get_success_url

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.movie = Movie.objects.get(name=self.kwargs['movie'])

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        movie = Movie.objects.get(name=self.kwargs['movie'])

        context['movie'] = movie
        context['page_name'] = 'Write Review'
        return context


class DeleteReview(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """allows user to delete a review that they wrote; removes record from database"""
    model = Review
    template_name = 'films/delete_review.html'
    context_object_name = 'review'

    # verify user; this is possible via UserPassesTestMixin
    def test_func(self):
        obj = self.get_object()
        return obj.user == self.request.user # returns a bool

    def get_success_url(self):
        return reverse_lazy('films:user_detail', kwargs={'pk': self.request.user.id, 'slug': self.request.user.slug }) # I don't think there's any need for this to be lazy?

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_name'] = 'Delete Review'
        return context

class CreateUML(LoginRequiredMixin, CreateView):

    model = UserMovieLink
    fields = [] # we are setting them all behind the scenes in form_valid; still, we must include this or the view won't work.

    login_url = 'login' # will be used by the LoginRequiredMixin if non-logged in user tries access

    def form_valid(self, form):
        # get the movie object via id captured from URLconf, packed in kwargs, stored in self (of this view instance)
        movie = Movie.objects.get(id=self.kwargs['pk'])

        form.instance.user = self.request.user
        form.instance.movie = movie

        if self.kwargs['action'] == 'mark_seen':
            form.instance.seen = True
        elif self.kwargs['action'] == 'mark_favorite':
            form.instance.favorite = True
            form.instance.seen = True
        elif self.kwargs['action'] == 'mark_watch_list':
            form.instance.watch_list = True

        return super().form_valid(form)

    def get_success_url(self):

        return reverse('films:movie', kwargs={'pk': self.object.movie.id, 'slug': self.object.movie.slug })


class UpdateUML(LoginRequiredMixin, UpdateView):

    model = UserMovieLink
    fields = []

    login_url = 'login'

    def form_valid(self, form):

        action = self.kwargs['action']

        if action == 'mark_seen':
            form.instance.seen = True

        elif action == 'unmark_seen':
            form.instance.seen = False

        elif action == 'mark_favorite':
            form.instance.seen = True
            form.instance.favorite = True

        elif action == 'unmark_favorite':
            form.instance.favorite = False

        elif action == 'mark_watch_list':
            form.instance.watch_list = True

        elif action == 'unmark_watch_list':
            form.instance.watch_list = False

        else:
            pass

        return super().form_valid(form)  # form gets saved


    def get_success_url(self):
        return reverse('films:movie', kwargs={'pk': self.object.movie.id, 'slug': self.object.movie.slug })


def mark_seen_view(request):

    data = {'success': False }

    if request.method == 'POST':
        user = request.user
        movie_id = request.POST.get('movie_id', None)

        movie = Movie.objects.get(id=movie_id)

        if UserMovieLink.objects.filter(user=user, movie=movie).exists():
            uml_ob = UserMovieLink.objects.get(user=user, movie=movie)
            message = 'Retrieved existing uml object | '
        else:
            uml_ob = UserMovieLink(user=user, movie=movie)
            message = 'Created a new uml object | '

        # if current state is False, switch it to true, and notify ajax function of new status via 'seen' in data
        if not uml_ob.seen:
            uml_ob.seen = True
            message += 'Seen now set to True'
            data['seen'] = True
        # current state is True, so toggle it to False
        else:
            uml_ob.seen = False
            uml_ob.favorite = False     # do not allow favorite = True for a movie that is not Seen
            message += 'Seen and Favorite now set to False'
            data['seen'] = False

        uml_ob.save()

        data['success'] = True
        data['message'] = message

        return JsonResponse(data)

def mark_favorite_view(request):

    data = {'success': False }

    if request.method == 'POST':
        user = request.user
        movie_id = request.POST.get('movie_id', None)

        movie = Movie.objects.get(id=movie_id)

        if UserMovieLink.objects.filter(user=user, movie=movie).exists():
            uml_ob = UserMovieLink.objects.get(user=user, movie=movie)
            message = 'Retrieved existing box object | '
        else:
            uml_ob = UserMovieLink(user=user, movie=movie)
            message = 'Created a new box object | '

        # if current state is False, switch it to true, and notify ajax function of this via 'fav' in data
        if not uml_ob.favorite:
            uml_ob.seen = True     # if user is turning Fav to True, then make sure Seen is also True
            uml_ob.favorite = True
            message += 'Favorite now set to True'
            data['favorite'] = True
        else:
            uml_ob.favorite = False
            message += 'Favorite now set to False'
            data['favorite'] = False

        uml_ob.save()

        data['success'] = True
        data['message'] = message

        return JsonResponse(data)

def mark_watch_view(request):

    data = {'success': False }

    if request.method == 'POST':
        user = request.user
        movie_id = request.POST.get('movie_id', None)

        movie = Movie.objects.get(id=movie_id)

        if UserMovieLink.objects.filter(user=user, movie=movie).exists():
            uml_ob = UserMovieLink.objects.get(user=user, movie=movie)
            message = 'Retrieved existing uml object | '
        else:
            uml_ob = UserMovieLink(user=user, movie=movie)
            message = 'Created a new uml object | '

        # if current state is False, switch it to true, and notify ajax function of this via 'watch' in data
        if not uml_ob.watch_list:
            uml_ob.watch_list = True
            message += 'Watchlist now set to True'
            data['watch_list'] = True
        else:
            uml_ob.watch_list = False
            message += 'Watchlist now set to False'
            data['watch_list'] = False

        uml_ob.save()

        data['success'] = True
        data['message'] = message

        return JsonResponse(data)



class GetRecommendations(LoginRequiredMixin, ListView):
    template_name = 'films/recommendations.html'
    context_object_name = 'movies'

    def get_queryset(self):
        """queryset returns movies that user hasn't marked seen and that aren't already in user's watchlist"""

        user = self.request.user

        # get all movies that user has not marked as seen nor added to their watchlist
        # remember that 'user_notes' is the related name defined on the Movie model for the m2m connection to User
        possible_movies = Movie.objects.exclude(user_notes=user, usermovielink__seen=True).exclude(user_notes=user,
            usermovielink__watch_list=True)

        # pick three movies from possible randomly (sample will not choose duplicates)
        three_chosen = sample(list(possible_movies), 3)

        return three_chosen

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_name'] = 'Recommendations'
        return context

class FaqView(TemplateView):
    template_name = 'films/faq.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_name'] = 'FAQ'
        return context

def contactView(request):
    if request.method == 'GET':
        form = ContactForm()
    else:
        form = ContactForm(request.POST)
        if form.is_valid():
            sender_subject = form.cleaned_data['subject']
            from_email = form.cleaned_data['from_email']
            subject = 'Received contact via NoirDB from {}'.format(from_email)
            message = sender_subject + '\n' + form.cleaned_data['message']
            admin_sender = 'admin@noirdb.com'
            try:
                send_mail(subject, message, admin_sender, ['support@noirdb.com'])
            except BadHeaderError:
                return HttpResponse('Invalid header found')
            return redirect('films:contact_success')

    return render(request, "films/contact.html", {'form': form, 'page_name': 'Contact'})

class ContactSuccessView(TemplateView):
    template_name = 'films/contact_success.html'

def get_top_five():
    """Query the db for the top five of highest rated + most reviewed Movies"""

    # this is simply a placeholder until I create the logic to query top movies based on num reviews and star ratings...
    t1 = Movie.objects.get(name__icontains='out of the past')
    t2 = Movie.objects.get(name__icontains='double indem')
    t3 = Movie.objects.get(name__icontains='big sleep')
    t4 = Movie.objects.get(name__icontains='scarlet street')
    t5 = Movie.objects.get(name__icontains='maltese falcon')

    top_five = [t1, t2, t3, t4, t5]

    return top_five



