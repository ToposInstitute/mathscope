from django.views.generic import TemplateView
from .forms import SearchForm

class IndexView(TemplateView):

    template_name = 'context/index.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['form'] = SearchForm()

        return context

class AboutView(TemplateView):

    template_name = 'context/about.html'

class SearchView(TemplateView):

    template_name = 'context/search.html'
