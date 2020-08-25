
from .models import Person, Movie, Cast, Job, Crew, Review, UserMovieLink, MediaLink

def get_stars():
    stars = [
        'Humphrey Bogart',
        'Dan Duryea',
        'Glenn Ford',
        'Rita Hayworth',
        'Ida Lupino',
        'Robert Ryan',
        'Burt Lancaster',
        'Gloria Graham',
        'Barbara Stanwyck',
        'Sterling Hayden',
        'Edward G. Robinson',
        'Lauren Bacall',
        'Dana Andrews',
        'Richard Conte',
        'Orson Welles',
        'William Holden',
        'Joan Bennett',
        'Fred MacMurray',
        'Gloria Swanson',
        'Jane Greer',
        'Robert Mitchum',
        'Veronica Lake',
        'James Cagney',
        'Alan Ladd',
        'Brian Donlevy',
        'Lizabeth Scott',
        'Peter Lorre',
        'Kirk Douglas',
        'Mary Astor',
        'Audrey Totter',
        "Edmond O'Brien",
        'Gene Tierney',
        'Vincent Price',
        'Ava Gardner',
    ]


    star_objects = []

    for star in stars:
        try:
            s_object = Person.objects.get(name__icontains=star.lower())
        except Person.DoesNotExist:
            print('Could not retrieve a Person object for {}'.format(star))

        else:
            star_objects.append(s_object)
            print('Added {} to list of Stars'.format(star))

    print('Gathered and returned {} Person objects.'.format(len(star_objects)))
    print('Total errors: {}'.format(len(stars) - len(star_objects)))

    return star_objects

def mark_starring_roles(actor):

    actor_cast_records = Cast.objects.filter(person=actor)

    for index, record in enumerate(actor_cast_records):
        record.starring_role = True
        record.save()

    print("All {} of {}'s roles have been marked as Starring Roles.".format(index, actor.name))









