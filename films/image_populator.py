import os
from django.core.files import File    # used to create the django image File object (see below)

from .models import Movie


def add_movie_poster(movie_object):
    """find and update the image field for a single movie object"""

    all_image_files = os.listdir('films/image_downloads/')

    movie_name = movie_object.name

    matching_image = None

    for image in all_image_files:
        if movie_name.lower() in image.lower():
            matching_image = image

    if matching_image:

        path_start = 'films/image_downloads/'
        filepath = '{}{}'.format(path_start, matching_image)

        image_object = open(filepath, 'rb')

        django_object = File(image_object)   # no need to call .read() on the opened object, django File() takes care of that.

        movie_object.poster_image.save(matching_image, django_object) # use of 'matching image' here: provides filename to save as

        image_object.close()

        print('Successfully added {} to {}'.format(matching_image, movie_name))

    else:
        print('No matching image file was found for the movie named {}'.format(movie_name))



# this function (and the required imports that go with it) could be moved over to my_functions to keep all your script
# functions in one single file.


# you are going to have to figure out how the literal filepaths given above, which are local to your system,
# will work when running this function during deployment. once the images have a specific location,
# you'll have to provide that location to this function for it to work correctly.





