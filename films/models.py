from django.db import models
from django.conf import settings                         # so we can use AUTH_USER_MODEL, per django docs
# from django.contrib.auth import get_user_model         # learndjango version
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from random import sample


#  person MUST be defined first, because Movie uses it (via references)
class Person(models.Model):
    """A person in the database"""
    name = models.CharField(max_length=150)
    dob = models.DateField(null=True, blank=True)
    dod = models.DateField(null=True, blank=True)
    
    slug = models.SlugField(
        default='',
        editable=False,
        max_length=150,
        )

    # this one will be tied to new jobs table
    #primary_occupation = models.CharField(max_length=80)
    bio_summary = models.TextField(default='', blank=True)

    class Meta:
        ordering = ['name']             # is this working? when?
        verbose_name_plural = 'people'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        kwargs = {
            'pk': str(self.id),
            'slug': self.slug
        }
        return reverse('films:person', kwargs=kwargs)

        # old, pre-slug version of the return:
        #return reverse('films:person', args=[str(self.id)])

    def save(self, *args, **kwargs):
        value_for_slug = self.name
        self.slug = slugify(value_for_slug, allow_unicode=True)
        super().save(*args, **kwargs)


class Movie(models.Model):
    """A movie in the database"""
    name = models.CharField(max_length=150)
    display_name = models.CharField(max_length=150, null=True)
    year = models.PositiveIntegerField(null=True)
    release_date = models.CharField(max_length=200, null=True)
    studio = models.CharField(max_length=100, default='', blank=True) # are these default empty strings really necessary ?
    based_on = models.CharField(max_length=800, default='', blank=True) # db wanted me to set a default after removing null=True

    slug = models.SlugField(
        default='',
        editable=True,
        max_length=150,
        )
    
    poster_image = models.ImageField(upload_to='posters/', blank=True) # remember that TYPE effects behavior of null= and blank=!

    film_summary = models.TextField(default='', blank=True)

    all_cast = models.ManyToManyField(Person, through='Cast', related_name='movies_cast')
    all_crew = models.ManyToManyField(Person, through='Crew', related_name='movies_crew')

    # you need to write a method for this class that checks its status each time its loaded, and updates
    # these attributes accordingly.
    rank = models.PositiveIntegerField(null=True)

    # these will be updated by update_review_details method
    num_reviews = models.PositiveIntegerField(null=True)
    avg_rating = models.FloatField(null=True)   # look into using DecimalField instead, though it has some 
                                                # required arguments and might have issues with SQLite !!
    
    user_notes = models.ManyToManyField(settings.AUTH_USER_MODEL, through='UserMovieLink', related_name='movies_notes')

    class Meta:
        ordering = ['year']  # this used to be name, make sure to migrate again 3/14

    def __str__(self):
        """Return a string representation of the model."""
        return self.name

    def get_absolute_url(self):
        kwargs = {
            'pk': str(self.id),
            'slug': self.slug
        }
        return reverse('films:movie', kwargs=kwargs)

        #old, pre-slug version:
        #return reverse('films:movie', args=[str(self.id)])

    def get_display_name(self):
        """This is handled by db populator script, but I have this hear in case I need to run it via shell"""
        if '(' in self.name:
            display_name = self.name.split('(')[0].strip() # remove (year) from title, for display purposes.
            return display_name
        else:
            return self.name

    def update_review_details(self):
        """Queries Review table to get all reviews of current movie object, then updates num_reviews and avg_rating"""
        
        movie_reviews = Review.objects.filter(movie=self)  
        if movie_reviews.count() == 0:
            self.avg_rating = None
            self.num_reviews = None
        else:
            self.num_reviews = movie_reviews.count()
            # get average of all reviews of this movie
            agg_result = Review.objects.filter(movie=self).aggregate(star_average=models.Avg('star_rating'))
            self.avg_rating = round(agg_result['star_average'], 1)  # would have been 'star_rating__avg' by default

        self.save() # this is crucial! this originally wasn't working becuase I forgot this line!

        # re: avg_rating above--
        # round(x, 1) will round x to 1 decimal place; without this, I can get results like .6666666, etc
        # add call to calculate_rank here, use it to update self.rank value...

    def get_related_movies(self):
        """a method to find three movies related to a given Movie instance; used with Daily Pick on front page"""

        # right now this works just on the director; later, if I add the 'starring' field to Movies, it will work
        # on the Movie's starring actors as well.

        # TODO: figure out how to use F objects and/or select_related to reduce database hits in this process!

        director = self.all_crew.get(crew__job__job_title='Director')
        # starring    to be added later

        # try-except isn't really necessary here because a query with no results will simply return an empty queryset.
        # get all movies by the same director
        same_director_films = Movie.objects.filter(crew__person=director, crew__job__job_title='Director').exclude(name=self.name)
        # remember that 'director' above is the actual Person object of the director, as retrieved further above.

        # return 3 or less movies by same director
        if same_director_films.count() > 3:
            return sample(list(same_director_films), 3)

        else:
            return same_director_films

    def save(self, *args, **kwargs):
        value_for_slug = self.name
        self.slug = slugify(value_for_slug, allow_unicode=True)
        super().save(*args, **kwargs)


class DailyMovie(models.Model):

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    date_posted = models.DateTimeField(auto_now_add=True)
    daily_count = models.PositiveIntegerField(default=0)
    active_movie = models.BooleanField(default=False)

    # constraint: only one record in DailyMovie table can have current_selection == True
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['active_movie'], condition=models.Q(active_movie=True), name='one active record only')   
        ]

    def __str__(self):
        info_string = 'Daily Movie #{} - {}'.format(self.daily_count, self.movie.display_name)
        return info_string

    def check_update_status(self):
        """If more than 1 day has passed since this movie was posted as daily movie, it's time for a new one"""

        elapsed_time = timezone.now() - self.date_posted # creates a timedelta object, which has attribute 'days'
        
        if elapsed_time.days < 1:
            return False
        else:
            return True


class Cast(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE) # can/ should you do null=True here ?
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)

    # additional fields
    role = models.CharField(max_length=200, blank=True)   # character they played in the movie

    def __str__(self):
        text = '{} as {} in {}'.format(self.person.name, self.role, self.movie.name)
        return text


class Job(models.Model):
    # this will simply store records for strings 'director', 'producer', etc.
    job_title = models.CharField(max_length=100)

    def __str__(self):
        return self.job_title


class Crew(models.Model):
    # linking models
    person = models.ForeignKey(Person, on_delete=models.CASCADE) # can / should you do null=True here?
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)

    # additional fields
    job = models.ForeignKey(Job, on_delete=models.CASCADE) # use a related name here? crews?

    # def __str__(self):
    #     text = self.person.name + ' was ' + self.job.job_title + ' of ' + self.movie.name
    #     return text

    def __str__(self):
        text = '{} was {} of {}'.format(self.person.name, self.job.job_title, self.movie.name)
        return text


class UserMovieLink(models.Model):
    """Intermediary table linking M2M between a Movie object and User object"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)

    seen = models.BooleanField(default=False, null=True, blank=True)
    favorite = models.BooleanField(default=False, null=True, blank=True)
    watch_list = models.BooleanField(default=False, null=True, blank=True)


    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'movie'], name='user_movie_unique')
        ]
    
    def __str__(self):
        text = "{}'s details for {}".format(self.user.username, self.movie.name)
        return text


class Review(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE) # related name? e.g. reviews (via User object)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE) # related name? e.g. reviews (via Movie object)
    
    date_added = models.DateTimeField(auto_now_add=True)

    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5

    rating_choices = [
        (ONE, 'Total Garbage... (One Star)'),       # can these be image links, referencing static files?
        (TWO, 'It was very Meh...  (Two Stars)'),
        (THREE, 'Solid, enjoyable... (Three Stars)'),
        (FOUR, 'Great, highly recommended... (Four Stars)'),
        (FIVE, 'An absolute Classic... (Five Stars)'),
    ]
    star_rating = models.PositiveSmallIntegerField(choices=rating_choices, default=THREE)

    review_text = models.TextField(default='', max_length=2000)

    # ideally instead of loading an error page, this should redirect to a 'You've already reviewed this...' message
    # however, the logic of the webpage prevents the Write Review button from showing up if it's already been revewied,
    # but still perhaps best practice to avoid this?
    
    # used to determine how many un-filled stars to print in template, based on star rating value.
    @property
    def get_empty_stars(self):
        return int(5-self.star_rating)

    class Meta:
        #db_table = 'review'         # I think this isn't necessary
        constraints = [
            models.UniqueConstraint(fields=['user', 'movie'], name='one_review_per_user')
        ]

    def __str__(self):
        if len(self.review_text) > 50:
            return f"{self.review_text[:50]}..."
        else:
            return f"{self.review_text}"

    # reviews only show up on a Movie detailview page, so the asbsolute_url is for the related Movie:
    def get_absolute_url(self):
        kwargs = {
            'pk': self.movie.id,
            'slug': self.movie.slug,
        }
        return reverse('films:movie', kwargs=kwargs)

    # override the save method so we can also call the relevant movie object's update method after the save
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # after the save, update review details for movie that just got reviewed
        self.movie.update_review_details()
        self.check_uml_status()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        # update review details for movie on review delete, too...
        self.movie.update_review_details()

    def check_uml_status(self):
        """this method simply creates and/or updates a UML object after a Review is written"""
        # what this solves: if user writes a Review of a movie, but never bothered to click 'add details',
        # this does it automatically, creating the UML object and updating Seen to True. if UML already 
        # exists (but user never clicked seen), it simply updates Seen to True.
        if UserMovieLink.objects.filter(user=self.user, movie=self.movie).exists():
            uml_object = UserMovieLink.objects.get(user=self.user, movie=self.movie)
            if uml_object.seen != True:
                uml_object.seen = True
                uml_object.save()
            else:
                pass # uml record exists and seen is already set to True
        else:
            uml_object = UserMovieLink.objects.create(user=self.user, movie=self.movie, seen=True)

        # a feeling: since the above method is -creating and/or modifying- UML model records, it seems like
        # it should be a method of UML, not of Review. Review could simply call it, instead of doing 
        # this work here. for now, though, it's a small and efficient bit of code, and is working
        # just fine, so I don't see a problem with leaving it here.


class MediaLink(models.Model):

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    url_link = models.URLField(max_length=800)
    host = models.CharField(max_length=200, default='')
    free = models.BooleanField(default=False)
    active = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['movie', 'url_link'], name='unique_movielink_matches')   
        ]

    def __str__(self):
        return self.url_link






