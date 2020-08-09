import os # used in add_movie_poster
import json
import re
from datetime import date
from django.core.files import File # used in add_movie_poster

from .models import Person, Movie, Cast, Job, Crew, Review, UserMovieLink, MediaLink

# order of script functions to populate the database, to run in the django shell:

# x. from films.models import *
# y. from films.my_functions import *
# 1. create_jobs()
# 2. get_people()   assign to all_people
# 3. for loop on all_people, call add_person on each person
# 4. get_movies()   assign to all_movies
# 5. create fail log:  flog = FailTracker()  only works on movie population, not people
# 6. for loop on all_movies, call add_movie on each movie
# 7. check for errors, as logged by the flog:  flog.fail_log

# 8. import the add_movie_poster function from image_populator.py
# 9. run a loop on all Movie objects, calling add_movie_poster() on each movie object


def create_jobs():
    """Updates the db to contain the 5 possible job records"""
    #Run this before anything else, so the 5 job records exist in db!

    d = 'Director'
    p = 'Producer'
    c = 'Cinematographer'
    w = 'Writer'
    cc = 'Composer'

    director = Job(job_title=d)
    director.save()
    producer = Job(job_title=p)
    producer.save()
    photog = Job(job_title=c)
    photog.save()
    writer = Job(job_title=w)
    writer.save()
    composer = Job(job_title=cc)
    composer.save()


def get_movies():
    """Import needed modules and load needed files"""

    filename = 'json_data/fin_movie_list.json'
    with open(filename) as fob:
        all_movies = json.load(fob)

    print('# Movies Loaded: {}'.format(len(all_movies))) 
    return all_movies


def get_people():

    filename = 'json_data/fin_people_list.json'
    with open(filename) as fob:
        all_people = json.load(fob)

    print('# People Loaded: {}'.format(len(all_people)))
    return all_people


class FailTracker():

    def __init__(self, dev_stage='testing'):
        self.dev_stage = dev_stage
        self.fail_log = {}

    def add_fail(self, movie_name, fail_note):

        if self.fail_log.get(movie_name): # check if movie key is already in dict
            self.fail_log[movie_name].append(fail_note) # fail note is a single string
        else:
            self.fail_log[movie_name] = [fail_note]  # value is a list, so it can appended to if more fails are found.

    def save_log(self):
        """Store the fail_log dictionary locally"""
        filename = 'json_data/fail_log.json'
        with open(filename, 'w') as fob:
            json.dump(self.fail_log, fob)

    def load_local_log(self):
        filename = 'json_data/fail_log.json'
        with open(filename) as fob:
            fails = json.load(fob)

        return fails


def get_year(release_date, title, flog):
    """Takes a string containing full release date and returns just the Year portion"""
    try:
        p = re.compile(r'\d{4}$')
    except:
        fail_note = 'get_year failed'
        flog.add_fail(title, fail_note)
        flog.save_log()
        return None
    else:
        return int(p.findall(release_date)[0])


def add_movie(movie_dict, flog):
    
    title = movie_dict['title']
    studio = movie_dict['studio']
    release_date = movie_dict['release date']
    year = get_year(movie_dict['release date'], title, flog)

    if '(' in title:
        display_name = title.split('(')[0].strip()
    else:
        display_name = title

    media_links = movie_dict['media_links']

    # current implementation of data set, the value of key 'based on' will be either
    # a string, 'n/a', or a list, with item 0 = work title, item 1 = author
    if movie_dict['based on'] == 'n/a':
        based_on = 'n/a'
    else:
        try:
            based_on = '{} by {}'.format(movie_dict['based on'][0], movie_dict['based on'][1])
        except:
            fail_note = 'add_movie - "Based On" list extraction failed for movie {}'.format(title)
            flog.add_fail(title, fail_note)
            flog.save_log()
        else:
            based_on = based_on.title() # this makes the 'by' get capitalized, which I don't like. 

            # other options:
            # based on has two strings in model: based on book title, based on author
            # then just use those as needed in the template
            # when it's just one big string, you have limited formatting options for it.

    # list of lists (actor-role, crew_job)
    cast_list = movie_dict['cast']
    crew_list = process_crew(movie_dict)

    # create the movie record
    try: 
        movie = Movie(name=title, display_name=display_name, year=year, release_date=release_date, studio=studio, based_on=based_on)
    except:
        fail_note = 'add_movie - Movie() call, {}'.format(title)
        flog.add_fail(title, fail_note)
        flog.save_log()

    # clearly we aren't going to try to add_cast and add_crew if the Movie() call failed        
    else:
        movie.save()
        # grab the pk of the movie record we just created above ... why though? what is this used for?
        movie_id = movie.id # this must be from some older version; it's apparently not used at all now

        # cast connections
        for actor_role_pair in cast_list:
            add_cast_member(actor_role_pair, movie, flog)

        # crew connections
        for crew_job_pair in crew_list:
            add_crew_member(crew_job_pair, movie, flog)

        # add media links, but only if at least 1 is preset.
        if media_links:
            for media_dict in media_links:
                add_media_link(movie, media_dict)


def add_media_link(movie, media_dict):
    """Add a record to the Media Link table"""

    url = media_dict['url']
    host = media_dict['host']
    free = media_dict['free']
    active = media_dict['active']

    media_record = MediaLink(movie=movie, url_link=url, host=host, free=free, active=active)
    media_record.save()


def add_cast_member(actor_role_pair, movie, flog):
    """call this to add ONE cast connection to Cast table"""

    person_name = actor_role_pair[0]
    person_role = actor_role_pair[1]

    try:
        person = Person.objects.get(name=person_name)

    except:
        fail_note = 'add_cast - Person linkage, {}, {}'.format(person_name, person_role)
        flog.add_fail(movie.name, fail_note)
        flog.save_log()

    else:
        try: 
            cast_credit = Cast(person=person, movie=movie, role=person_role)
        except:
            fail_note = 'add_cast - Cast() call, {}, {}'.format(person_name, person_role)
            flog.add_fail(movie.name, fail_note)
            flog.save_log()
        else:
            cast_credit.save()



def process_crew(movie_dict):
    """takes movie object, returns a list of lists, containing all individual crew members and their job on movie"""

    director = movie_dict['director']
    camera = movie_dict['camera']
    composer = movie_dict['composer']

    producer_list = movie_dict['producer']
    writer_list = movie_dict['writers']

    crew_and_job = []

    crew_and_job.append([director, 'Director']) 
    crew_and_job.append([camera, 'Cinematographer'])
    
    null_composers = ['uncredited', 'none listed']

    # composer is the only crew type that might have a 'no value' string; check for it here, and if so,
    # do not add it to the crew_and_job list.
    if composer.lower() in null_composers:
        pass
    else:
        crew_and_job.append([composer, 'Composer'])

    for producer in producer_list:
        crew_and_job.append([producer, 'Producer'])
    for writer in writer_list:
        crew_and_job.append([writer, 'Writer'])

    return crew_and_job

    
def add_crew_member(crew_job_pair, movie, flog):
    """Call this to add ONE crew connection to crew table"""

    crew_name = crew_job_pair[0]
    crew_type = crew_job_pair[1]

    try:
        job = Job.objects.get(job_title=crew_type)

    except:
        fail_note = 'add_crew - Job linkage, {}, {}'.format(crew_name, crew_type)
        flog.add_fail(movie.name, fail_note)
        flog.save_log()
    
    else:
        # we don't want to add the person if we couldn't find what job they had, so this is indented
        try:
            person = Person.objects.get(name=crew_name)
        except:
            fail_note = 'add_crew - Person linkage, {}, {}'.format(crew_name, crew_type)
            flog.add_fail(movie.name, fail_note)
            flog.save_log()
        else:
            try:
                crew_credit = Crew(person=person, movie=movie, job=job)
            except:
                fail_note = 'add_crew - Crew() call, {}, {}'.format(crew_name, crew_type)
                flog.add_fail(movie.name, fail_note)
                flog.save_log()
            else:
                crew_credit.save()  # you might need to put the .sav() call in the try block


def reformat_date(date_string):
    """takes a date in string form and returns a datetime.date object"""
    # note: we already verified correct format of all dob, dod strings in the verify_date_format function
    # in 'date_fix_fin.py'. So we don't need to check it again here.
    
    date_object = date.fromisoformat(date_string)
    return date_object


def add_person(person_dict):
    """Add a Person record to the database"""

    # note: this function doesn't use the fail_log because I already succesfully updated db with it.

    dob_string = person_dict['dob'] 
    dod_string = person_dict['dod']
    name_string = person_dict['name']

    if not dob_string: # 'if not' syntax will check against both an empty string '' and a None type.
        dob_object = None
    else:
        dob_object = reformat_date(dob_string) # revise these to include possibility of None result (returned from refromat date)

    if not dod_string:
        dod_object = None
    else:
        dod_object = reformat_date(dod_string)

    # build the person from the Person model (imported from django project)
    person = Person(name=name_string, dob=dob_object, dod=dod_object)

    # save this person to the database
    person.save()


def add_movie_poster(movie_object):
    """find and update the image field for a single movie object"""

    all_image_files = os.listdir('films/image_downloads/') # simply lists names of the files, as strings

    movie_name = movie_object.name

    matching_image = None # this will simply be a string, used to access the appropriate file

    # compare each image string against the name of the movie, to find a match
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

    # note: the call to .save() on attribute poster_image also saves the movie_object itself







