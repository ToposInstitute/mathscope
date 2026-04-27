import argparse

from context.models import *
from conllu import parse_incr
from django.core.management.base import BaseCommand, CommandError
from tqdm import tqdm

class Command(BaseCommand):
    help = "Load a CONLL-U collection into the database."

    def add_arguments(self, parser):

        parser.add_argument('--name', type=str, default='Default')
        parser.add_argument('filename', type=argparse.FileType('r'))

    def handle(self, *args, **kwargs):

        collection = Collection.objects.get_or_create(
            name=kwargs['name'],
        )[0]
        current_document = None
        for sentence in tqdm(parse_incr(kwargs['filename'])):
            if 'doc_id' in sentence.metadata:
                document = Document(
                    title=sentence.metadata.get('doc_title', "Untitled"),
                    url=sentence.metadata['doc_url'],
                    collection=collection,
                )
                document.save()
                current_document = document

            if current_document is None:
                print("No document available.")
                continue

            sentence_model = Sentence(
                document=current_document,
                text=sentence.metadata['text'],
            )
            sentence_model.save()

            lemmas = []

            for token in sentence:
                if token['feats']:
                    features = '|'.join('%s=%s' % (key, value) for (key, value)
                                        in token['feats'].items())
                else:
                    features = ""
                if token['misc']:
                    misc = '|'.join('%s=%s' % (key, value) for (key, value) in
                                    token['misc'].items())
                else:
                    misc = ""
                token_model = Token(
                    sentence=sentence_model,
                    index=int(token['id']),
                    form=token.get('form', ''),
                    lemma=token.get('lemma', ''),
                    upos=token.get('upos', ''),
                    xpos=token.get('xpos', ''),
                    features=features,
                    head=int(token['head']) if token['head'] else None,
                    deprel=token.get('deprel', ''),
                    misc=misc,
                )
                if token_model.lemma:
                    lemmas.append(token_model.lemma)
                token_model.save()
            sentence_model.lemmas = ' '.join(lemmas)
            sentence_model.save()
