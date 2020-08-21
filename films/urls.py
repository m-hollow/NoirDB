"""Defines URL patterns for films app"""

from django.urls import path
from .views import (IndexPage, MovieList, FreeMoviesList, MovieDetail, PersonList, PersonDetail, SearchResults, WriteReview,
    DeleteReview, UserDetail, CreateUML, UpdateUML, GetRecommendations, FaqView, contactView, ContactSuccessView, autocomplete_view)

app_name = 'films'
urlpatterns = [
    # Home Page
    path('', IndexPage.as_view(), name='index'),
    # Page that shows all Movies
    path('all_movies/', MovieList.as_view(), name='all_movies'),

    path('free_movies/', FreeMoviesList.as_view(), name='free_movies'),

    # Page that shows a single Movie
    path('movie/<int:pk>-<str:slug>/', MovieDetail.as_view(), name='movie'),

    # Page that shows all people
    path('all_people/', PersonList.as_view(), name='all_people'),

    # Page for a single Person
    path('person/<int:pk>-<str:slug>/', PersonDetail.as_view(), name='person'),

    # Page that shows user Search Results
    path('results/', SearchResults.as_view(), name='search_results'),

    # Page that allows user to enter a Review of a Movie
    path('write_review/<movie>/', WriteReview.as_view(), name='write_review'),  # should we use converter to string? <str:movie>

    # Page for deleting an existing review
    path('delete_review/<int:pk>/', DeleteReview.as_view(), name='delete_review'),

    # Page for the logged-in user, showing their details
    path('user_detail/<int:pk>-<str:slug>/', UserDetail.as_view(), name='user_detail'),


    # creates a record in UserMovieLink table, connecting user to movie
    path('create_uml/<int:pk>/<action>/', CreateUML.as_view(), name='create_uml'),

    # one single URL pattern / path for doing any kind of update to UserMovieLink record; captures id of UML object as well as 'action' string
    # the action string is used in the view to determine which action to perform on the object
    path('update_uml/<int:pk>/<action>/', UpdateUML.as_view(), name='update_uml'),

    path('recommendations/', GetRecommendations.as_view(), name='get_recommendations'),

    path('faq/', FaqView.as_view(), name='faq'),

    path('contact/', contactView, name='contact'),

    path('contact_success/', ContactSuccessView.as_view(), name='contact_success'),

    path('auto_comp/', autocomplete_view, name='autocomplete'),

    ]


