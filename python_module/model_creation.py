import gensim.matutils
from gensim import corpora
from gensim.models import TfidfModel
from gensim.models import CoherenceModel
from gensim.models import LsiModel
from gensim.models import nmf

dataset = corpora.Dictionary()

def add_words_to_dictionary(tokens):
    dataset.add_documents(tokens)

def create_corpus_and_vectorizer(tokens):
    corpus = [dataset.doc2bow(token) for token in tokens]
    tfidf_vect = TfidfModel(corpus)
    return corpus,tfidf_vect


def get_best_model(token_list,min_topic_num=3,max_topic_num=14, coherence_metric="c_v", model_type ="lsi"):
    model_list = []
    coherence_values = []
    #create the corpus for the model 
    corpus,tfidf_vect = create_corpus_and_vectorizer(token_list)
    for topics_num in range(min_topic_num,max_topic_num + 1):
        #Create the LsiModels with increasing number of Topics\
        if model_type == "nmf":
            model = nmf.Nmf(tfidf_vect[corpus], id2word=dataset, num_topics=topics_num)
        else:
            model = LsiModel(tfidf_vect[corpus], id2word=dataset, num_topics=topics_num)
        model_list.append(model)
        
        topics_model= [[word for word, prob in topic] for topicid, topic in model.show_topics(formatted=False)]
        #Create the CoherenceModel and evaluate its score
        coherence_model = CoherenceModel(topics=topics_model, texts=token_list,
                dictionary=dataset,coherence=coherence_metric,
                window_size=30)
        coherence_values.append(coherence_model.get_coherence())
    try:
        index_value = coherence_values.index(max(coherence_values))
    except:
        index_value = 0
    best_model = model_list[index_value]
    return best_model, corpus


def apply_dataframe_to_model(model,used_corpus,tokens,normalize=False):
    new_corpus = [dataset.doc2bow(tokens)]
    #we use a tfidf vectorizer based on the corpus for the training model
    tfidf_vectorizer = TfidfModel(used_corpus)
    tfidf_vector= tfidf_vectorizer[new_corpus]
    return get_distrib_as_dict(model[tfidf_vector],normalize)


def get_distrib_as_dict(vector, normalize = False):
    distribs = {}
    for dist in vector:
        distribs = dict((int(x),float(y)) for x,y in dist)
    if normalize:
        max_value = max(distribs.values())
        min_value = min(distribs.values())
        for key in distribs:
            distribs[key] = (distribs[key]-min_value)/(max_value-min_value)
    return distribs