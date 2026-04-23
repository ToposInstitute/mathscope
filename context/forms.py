from django import forms
from django.utils.translation import gettext as _
from .models import *

class SearchForm(forms.Form):
    """
    The default Mathoscope search form, which allows the user to construct a
    query for searching data in a contextual corpus.
    """

    template_name = "context/search_form.html"

    #: The text query input.
    query = forms.CharField(
        label=_("Query"),
        required=True,
    )

    #: The collections to search.
    collections = forms.ModelMultipleChoiceField(
        Collection.objects.all().order_by('-priority'),
        label=_("Collections"),
        initial=Collection.objects.all(),
    )
