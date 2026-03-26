import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os 

# Import the wordcloud library
from wordcloud import WordCloud
import re
import nltk

from pprint import pprint

# Gensim
import gensim
import gensim.corpora as corpora
from gensim.utils import simple_preprocess
from gensim.models import CoherenceModel

# spacy for lemmatization
import spacy

# Plotting tools
import pyLDAvis
import pyLDAvis.gensim  # don't skip this

# Enable logging for gensim - optional
import logging
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.ERROR)

import warnings
warnings.filterwarnings("ignore",category=DeprecationWarning)

#nltk.download('stopwords')

csv_file_path = "google_alerts/yourmoralsalerts/data/"
txt_files_path = "texts/"
model_path = "models/"
viz_path = "viz/"

evaluation = True


def main():
    n = len(os.listdir(csv_file_path))
    print(f"Analysing {n} csv files...")

    if not os.path.exists(model_path):
        os.mkdir(model_path)
    if not os.path.exists(txt_files_path):
        os.mkdir(txt_files_path)
    if not os.path.exists(viz_path):
        os.mkdir(viz_path)    

    all_words = []
    count_all_alerts = 0
    for file in os.listdir(csv_file_path):
        if file.endswith(".csv"):
            print(f"Analyzing {file}...")
            df = pd.read_csv(csv_file_path + file)
            print("Number of alerts before preprocessing: ", len(df))
            df = df.dropna(subset=['Text'])
            df = df[df['Reachable']]
            df = df.reset_index(drop=True)
            print(f"Number of alerts: {len(df)}")
            count_all_alerts += len(df)

            def sent_to_words(sentences):
                """Tokenize the sentences into words."""
                for sentence in sentences:
                    yield(gensim.utils.simple_preprocess(str(sentence), deacc=True))

            # Create a list of texts
            texts = df['Text'].values.tolist()

            # Remove Emails
            texts = [re.sub('\S*@\S*\s?', '', sent) for sent in texts]

            # Remove new line characters
            texts = [re.sub('\s+', ' ', sent) for sent in texts]

            # Remove distracting single quotes
            texts = [re.sub("\'", "", sent) for sent in texts]

            # Tokenize words and Clean-up text
            data_words = list(sent_to_words(texts))

            all_words.extend(data_words)
    print("Total number of alerts: ", count_all_alerts)
    
    def compute_coherence_values(dictionary, corpus, texts, limit, start=2, step=3):
        """
        Compute c_v coherence for various number of topics

        Parameters:
        ----------
        dictionary : Gensim dictionary
        corpus : Gensim corpus
        texts : List of input texts
        limit : Max num of topics

        Returns:
        -------
        model_list : List of LDA topic models
        coherence_values : Coherence values corresponding to the LDA model with respective number of topics
        """
        coherence_values = []
        model_list = []
        for num_topics in range(start, limit, step):
            print("Computing coherence for", num_topics, "topics...")
            model = gensim.models.ldamodel.LdaModel(corpus=corpus,
                                            id2word=id2word,
                                            num_topics=num_topics, 
                                            update_every=1,
                                            chunksize=100,
                                            passes=10,
                                            alpha='auto',
                                            per_word_topics=True)
            model_list.append(model)
            coherencemodel = CoherenceModel(model=model, texts=texts, dictionary=dictionary, coherence='c_v')
            coherence_values.append(coherencemodel.get_coherence())
            print("Coherence computed: ", coherencemodel.get_coherence())

        return model_list, coherence_values

    stop_words = set(nltk.corpus.stopwords.words('french') + nltk.corpus.stopwords.words('english'))

    # Build the bigram and trigram models
    bigram = gensim.models.Phrases(all_words, min_count=5, threshold=100) # higher threshold fewer phrases.
    trigram = gensim.models.Phrases(bigram[all_words], threshold=100)  

    # Faster way to get a sentence clubbed as a trigram/bigram
    bigram_mod = gensim.models.phrases.Phraser(bigram)
    trigram_mod = gensim.models.phrases.Phraser(trigram)

    # Define functions for stopwords, bigrams, trigrams and lemmatization
    def remove_stopwords(texts):
        return [[word for word in simple_preprocess(str(doc)) if word not in stop_words] for doc in texts]

    def make_bigrams(texts):
        return [bigram_mod[doc] for doc in texts]

    def make_trigrams(texts):
        return [trigram_mod[bigram_mod[doc]] for doc in texts]

    def lemmatization(texts, allowed_postags=['NOUN', 'ADJ', 'VERB', 'ADV']):
        """https://spacy.io/api/annotation"""
        texts_out = []
        for sent in texts:
            doc = nlp(" ".join(sent)) 
            texts_out.append([token.lemma_ for token in doc if token.pos_ in allowed_postags])
        return texts_out
    
    print("Preprocessing data: lemmatizing, make bigrams...")
    # Remove Stop Words
    all_words_nostops = remove_stopwords(all_words)

    # Form Bigrams
    data_words_bigrams = make_bigrams(all_words_nostops)

    # Initialize spacy 'fr' model, keeping only tagger component (for efficiency)
    # python3 -m spacy download en
    nlp = spacy.load("fr_core_news_sm")

    # Do lemmatization keeping only noun, adj, vb, adv
    data_lemmatized = lemmatization(data_words_bigrams, allowed_postags=['NOUN', 'ADJ', 'VERB', 'ADV'])

    # Create Dictionary
    id2word = corpora.Dictionary(data_lemmatized)

    # Create Corpus
    texts = data_lemmatized

    # Term Document Frequency
    corpus = [id2word.doc2bow(text) for text in texts]
    if evaluation:
        # Compute Coherence Score
        start = 15
        limit = 16
        model_list, coherence_values = compute_coherence_values(dictionary=id2word, corpus=corpus, texts=data_lemmatized, start=start, limit=limit, step=1)
        best_model = model_list[np.argmax(coherence_values)]
        print(f"Best model: {np.argmax(coherence_values) + start}")
        best_model.save(model_path + "lda_best.model")
    else:
        best_model = gensim.models.LdaModel.load(model_path + "lda_best.model")


    # Visualize the topics
    print("Visualizing topics...")
    vis_2 = pyLDAvis.gensim.prepare(best_model, corpus, id2word, sort_topics=False)
    pyLDAvis.save_html(vis_2, viz_path + "vis_best.html")
    print("Done!")
    
if __name__ == "__main__":
    main()
