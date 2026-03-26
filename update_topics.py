import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os 
import re
import nltk


# Gensim
import gensim
import gensim.corpora as corpora
from gensim.utils import simple_preprocess

# spacy for lemmatization
import spacy

csv_file_path = "google_alerts/yourmoralsalerts/data/"

lda_model = gensim.models.LdaMulticore.load("models/lda_best.model")

def create_corpus(text):

    text = re.sub('\S*@\S*\s?', '', text)  # Remove emails
    text = re.sub('\s+', ' ', text)  # Remove new line characters
    text = re.sub("\'", "", text) # Remove distracting single quotes



    def sent_to_words(sentence):
        """Tokenize the sentences into words."""
        yield(gensim.utils.simple_preprocess(str(sentence), deacc=True))    

    # Tokenize words and Clean-up text
    data_words = list(sent_to_words(text))
    stop_words = set(nltk.corpus.stopwords.words('french') + nltk.corpus.stopwords.words('english'))

    # Build the bigram and trigram models
    bigram = gensim.models.Phrases(data_words, min_count=5, threshold=100) # higher threshold fewer phrases.
    trigram = gensim.models.Phrases(bigram[data_words], threshold=100)  

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

    # Remove Stop Words
    all_words_nostops = remove_stopwords(data_words)

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

    return corpus

def main():
    n = len(os.listdir(csv_file_path))
    print(f"Analysing {n} csv files...")

    all_words = []
    for file in os.listdir(csv_file_path):
        if file.endswith(".csv"):
            print(f"Analyzing {file}...")
            df = pd.read_csv(csv_file_path + file)
            df = df.dropna(subset=['Text'])
            df = df[df['Reachable']]
            df = df.reset_index(drop=True)
            print(f"Number of alerts: {len(df)}")
            topic_nums = []
            prop_topics = []
            topic_keywords_t = []
            sec_topic_nums = []
            sec_prop_topics = []
            sec_topic_keywords_t = []
            true_topic_nums = []
            true_prop_topics = []
            true_topic_keywords_t = []
            print("Computing topics for each text...")
            count = 1
            for i in range(len(df)):
                if count % 20 == 0:
                    print(f"Computing topic for text {count}/{len(df)}")
                text = df.loc[i, 'Text']
                corpus = create_corpus(text)
                topics = lda_model[corpus]
                for i, row in enumerate(topics):
                    row = sorted(row[0], key=lambda x: (x[1]), reverse=True)
                    if len(row) < 3:
                        true_prop_topics.append(None)
                        true_topic_keywords_t.append(None)
                        true_topic_nums.append(None)
                    if len(row) < 2:
                        sec_prop_topics.append(None)
                        sec_topic_keywords_t.append(None)
                        sec_topic_nums.append(None)
                    # Get the Dominant topic, Perc Contribution and Keywords for each document
                    for j, (topic_num, prop_topic) in enumerate(row):
                        if j == 0:  # => dominant topic
                            wp = lda_model.show_topic(topic_num)
                            topic_keywords = ", ".join([word for word, prop in wp])
                            topic_nums.append(int(topic_num))
                            prop_topics.append(round(prop_topic,4))
                            topic_keywords_t.append(topic_keywords)
                        elif j == 1:
                            wp = lda_model.show_topic(topic_num)
                            topic_keywords = ", ".join([word for word, prop in wp])
                            sec_topic_keywords_t.append(topic_keywords)
                            sec_topic_nums.append(int(topic_num))
                            sec_prop_topics.append(round(prop_topic,4))
                        elif j == 2:
                            wp = lda_model.show_topic(topic_num)
                            topic_keywords = ", ".join([word for word, prop in wp])
                            true_topic_keywords_t.append(topic_keywords)
                            true_topic_nums.append(int(topic_num))
                            true_prop_topics.append(round(prop_topic,4))
                        else:
                            break
                count += 1
            df['True_Topic'] = true_topic_nums
            df['True_Perc_Contribution'] = true_prop_topics
            df['True_Topic_Keywords'] = true_topic_keywords_t
            df['Dominant_Topic'] = topic_nums
            df['Perc_Contribution'] = prop_topics
            df['Topic_Keywords'] = topic_keywords_t
            df['Second_Topic'] = sec_topic_nums
            df['Second_Perc_Contribution'] = sec_prop_topics
            df['Second_Topic_Keywords'] = sec_topic_keywords_t
            df = df.drop(columns=['Text'])
            if not os.path.exists("result/"):
                os.mkdir("result/")
            df.to_csv(f"result/topic_dist_{file}", index=False)
                
    
if __name__ == "__main__":
    main()