from itertools import chain
from operator import attrgetter
from random import sample

from django.shortcuts import render, redirect, get_object_or_404
#from django.contrib.auth.decorators import login_required          # no longer used after switch to class-based views
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404, HttpResponse
from django.urls import reverse, reverse_lazy
from django.core.mail import send_mail, BadHeaderError

from django.contrib.auth import get_user_model # this is here so user_detail view can set its model to user Model

from django.views.generic import (TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView)
from .models import (Person, Movie, Cast, Job, Crew, Review, UserMovieLink, MediaLink)
from .forms import ReviewForm, ContactForm

# A BIG Question: why aren't you using Table-level queries in your views, using all the models listed directly above?
# you are not resrtriced to just using the record-level object instance that is available in the view, you can also
# do table-level queries with any of the Models above, they have all been imported to this file!

# my new class-based views

class IndexPage(TemplateView):
    template_name = 'films/index.html'


class MovieList(ListView):
    paginate_by = 30
    queryset = Movie.objects.order_by('name')
    template_name = 'films/all_movies.html'
    context_object_name = 'all_movies'


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

        # get all Person objects from this Movie's cast
        cast = self.object.all_cast.all().order_by('name')

        cast_role_pairs = [] # store a Person object and role they played together in a list, in this list.

        # get the role each person played from the intermediary table Cast, store both  (person and role) together
        for person in cast:
            role_played = person.cast_set.get(movie=self.object).role # grab role attribute from record instance returned by get()
            #role_played = self.object.cast_set.get(person=person).role
            cast_role_pairs.append([person, role_played])

        # note: alternate way to query for cast + role is to query on Cast table itself, retreiving instances
        # of Cast objects for this movie, then store the Person.name and role field from each record.

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
        context['cast_list'] = cast_role_pairs
        context['reviews'] = movie_reviews
        context['media_links'] = media_links
        context['user_review'] = user_review       # value is Review object or None
        context['user_movie_details'] = user_movie_details  # value is UserMovieLink object or None
        context['actions'] = action_dict

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

        # first thing: yes, you an access 'search_results' inside the context object here, after the call to
        # super and assignment to context
        # second thing: amazingly, the pagination still works even if the displayed items are not from the
        # default context structure, which is 'search_results'. Here, I divide those up into new new entries
        # into the context (Movies and People) and then display those -- the pagination works exaclty as if 
        # I was displaying the results from search_results, it doesn't care that I'm displaying them via the
        # other, non-default context keys. this must mean that the behind-the-scenes pagination that ListView
        # is doing will simply work on --whatever objects are returned by get_queryset, regardless of how they
        # are packaged in the context--. This must be true, because my objects still indeed came from the results
        # of get_queryset, they are just stored in a different part of the context. (but these might just all
        # be references to the objects, anyway, most likely....)

        # this new approach means I don't actually need the custom template tag filter 'get_class', because I'm now
        # sorting this objects here, in this view, instead of sorting them in the template with the custom
        # tag filter.

        search_results = context['search_results']

        for result in search_results:
            if isinstance(result, Movie):
                movie_results.append(result)
            else:
                people_results.append(result)


        # the problem with this approach is that you are sending duplicate data in the context;
        # 'search_results' already contains ALL the queried db objects; in order to split them up, 
        # you've loaded them into new lists, and sent those lists in the context along with the original
        # 'search_results' (which is the default objects, just renamed). BUT WAIT, perhaps these are all
        # just references to the actual objects, in which case it doesn't really matter, does it? 

        context['movie_results'] = movie_results
        context['people_results'] = people_results

        return context

    def get_queryset(self):
        
        query = self.request.GET.get('q') # self is the instance of the class-based view, create per-use.
        
        movie_list = Movie.objects.filter(name__icontains=query).order_by('name')
        person_list = Person.objects.filter(name__icontains=query).order_by('name') 

        total_list = sorted(chain(movie_list, person_list), key=attrgetter('name'))

        # Q: isn't it redundant to use both order_by() on the query and sorted() on the total list?

        self.count = len(total_list) # update the count so it can be displayed in results

        return total_list


class UserDetail(LoginRequiredMixin, DetailView): # I'm assuming this mixin works on DetailView as well as CreateView...
    model = get_user_model()
    template_name = 'films/user_detail.html'

    query_pk_and_slug = True

    login_url = 'users:login' # will be used by the LoginRequiredMixin if non-logged in user tries access

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # original version, packaging movies into context; I've since switched to UML objects
        # seen_movies = self.object.movies_notes.filter(usermovielink__seen=True).order_by('name')
        # favorite_movies = self.object.movies_notes.filter(usermovielink__favorite=True).order_by('name')
        # watch_list_movies = self.object.movies_notes.filter(usermovielink__watch_list=True).order_by('name')

        # new version, query UML objects and package into conext
        uml_seen = self.object.usermovielink_set.filter(seen=True).order_by('movie__name')
        uml_favs = self.object.usermovielink_set.filter(favorite=True).order_by('movie__name')
        uml_watch = self.object.usermovielink_set.filter(watch_list=True).order_by('movie__name')

        # figure out how to order by movie name (above) answer: double underscore, since it's a field on a related model, 
        # and not the one you are actually retreiving.

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

        # no longer used, replaced by uml packages below
        # context['seen_movies'] = seen_movies
        # context['favorites'] = favorite_movies
        # context['watch_list'] = watch_list_movies
        
        context['uml_seen'] = uml_seen
        context['uml_favs'] = uml_favs
        context['uml_watch'] = uml_watch

        context['user_reviews'] = user_reviews
        context['actions'] = action_dict

        return context


class WriteReview(LoginRequiredMixin, CreateView):

    # create view does NOT have a get_queryset method! that is for DetailView and ListView
    model = Review
    template_name = 'films/write_review.html'
    context_object_name = 'review'      # I think this is unnecessary, the template is for form display...
    
    form_class = ReviewForm

    login_url = 'users:login' # will be used by the LoginRequiredMixin if non-logged in user attempts access

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


class CreateUML(LoginRequiredMixin, CreateView):

    model = UserMovieLink
    fields = [] # we are setting them all behind the scenes in form_valid; still, we must include this or the view won't work.

    login_url = 'users:login' # will be used by the LoginRequiredMixin if non-logged in user tries access

    def form_valid(self, form):
        # get the movie object via name captured from URLconf, packed in kwargs, stored in self (of this view instance)
        movie = Movie.objects.get(name=self.kwargs['movie'])

        form.instance.user = self.request.user
        form.instance.movie = movie
        
        return super().form_valid(form)

    def get_success_url(self):
        # this will use the movie objects get_absolute_url method
        # return redirect(movie)    # NOTE: this didn't work! but I'm not sure why it failed. error read:
        # "Reverse for 'films.views.movie' not found. 'films.views.movie' is not a valid view function or pattern name."
        
        # DUH: the movie object is only retrieved in the form_valid METHOD, not in THIS method. it had no
        # idea what 'movie' was. you either have to query it again in this method, or query it as an attribute
        # assignment on the class, so it can be used in these methods.

        return reverse('films:movie', kwargs={'pk': self.object.movie.id, 'slug': self.object.movie.slug })


class UpdateUML(LoginRequiredMixin, UpdateView):
    """the logic in the form_valid method: could you move this to a method in the UML model itself? or would that require"""
    # a bunch of additional code to process the Form, thereby failing to leverage the power of the UpdateView ?

    model = UserMovieLink
    fields = []

    login_url = 'users:login'

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

class FaqView(TemplateView):
    template_name = 'films/faq.html'


def contactView(request):
    if request.method == 'GET':
        form = ContactForm()
    else:
        form = ContactForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            from_email = form.cleaned_data['from_email']
            message = form.cleaned_data['message']
            try:
                send_mail(subject, message, from_email, ['admin@example.com'])
            except BadHeaderError:
                return HttpResponse('Invalid header found')
            return redirect('films:contact_success')

    return render(request, "films/contact.html", {'form': form})

class ContactSuccessView(TemplateView):
    template_name = 'films/contact_success.html'




# my original function-based views

# def index(request):
#     """The homepage for FNDB."""
#     return render(request, 'films/index.html')

# def all_movies(request):
#     """Show all movies in database"""
#     movies = Movie.objects.all()
#     context = {'movies': movies}
#     return render(request, 'films/all_movies.html', context)

# def movie(request, movie_id):
#     """Show a page for a single movie"""
#     movie = Movie.objects.get(id=movie_id)

#     people = movie.people.exclude(credit__occupation='director') # filter by primary_occ = actor so only actors display in cast
#     credits = movie.credit_set.all()

#     # use get(), not filter(), because we know we want just One object
    
#     director = movie.people.get(credit__occupation='director')

#     person_credit_pairs = list(zip(people, credits))  # list of tuples, each tuple is:
#                                                       # (person instance, credit instance)

#     context = {'movie': movie, 'pair_tuples': person_credit_pairs, 'director': director}

#     return render(request, 'films/movie.html', context)

# def person(request, person_id):
#     """Show a page for a single person"""
#     person = Person.objects.get(id=person_id)
    
#     movies = person.movies.all()   # using related name 'movies', which overrides movie_set 

#     credits = person.credit_set.all()

#     movie_credit_pairs = list(zip(movies, credits))

#     context = {'person': person, 'pair_tuples': movie_credit_pairs}

#     return render(request, 'films/person.html', context)



