from django.contrib import admin

from .models import Person, Movie, Cast, Crew, Job, Review, UserMovieLink, MediaLink

admin.site.register(Person)
admin.site.register(Movie)
admin.site.register(Cast)
admin.site.register(Crew)
admin.site.register(Job)
admin.site.register(Review)
admin.site.register(UserMovieLink)
admin.site.register(MediaLink)