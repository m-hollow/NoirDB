from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

class CustomUser(AbstractUser):
    num_movies_rated = models.PositiveIntegerField(null=True, blank=True)
    num_movies_reviewed = models.PositiveIntegerField(null=True, blank=True)

    slug = models.SlugField(
        default='',
        editable=False,
        max_length=200,
        )

    def get_absolute_url(self):
        kwargs = {
            'pk': str(self.id),
            'slug': self.slug
        }
        return reverse('films:user_detail', kwargs=kwargs)

    def save(self, *args, **kwargs):
        value_for_slug = self.username
        self.slug = slugify(value_for_slug, allow_unicode=True)
        super().save(*args, **kwargs)

        # old version, pre-slug:
        #return reverse('films:user_detail', args=[str(self.id)])





    # above fields should be a queryset + SUM() equivalent
    # though then there is the question, when are they updated? 
    # answer: probably the view that loads the UserDetail page should update them every time the user page is loaded...?



