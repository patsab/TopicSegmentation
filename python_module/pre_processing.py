import spacy
import string


# define space nlp with just the tagger (includes lemmatizer)
nlp_spacy = spacy.load('en_core_web_trf', disable=['parser', 'ner'])
nlp_spacy_deu = spacy.load('de_core_news_lg',disable=['parser', 'ner'] )

# adding aditional stop words
additional_stopwords = {'#cough', '#sneeze', '#bs', '#breath', '#ahm', 'deu','sabine','sandra','eva','dominik','katrin','girl','tomorrow', 'yesterday','johannes'}
nlp_spacy.Defaults.stop_words |= additional_stopwords
nlp_spacy.Defaults.stop_words |= set(string.punctuation)


# synonyms
synonyms = {
    "ja": "yes"
}

def replace_with_syn(token):
    if token in synonyms:
        return synonyms[token]
    return token

def tokenize(text, lang='en'):
    if lang == 'ger':
        return tokenize_german(text)
    else:
        return tokenize_eng(text)

#tokenization and pre-processing with spacy
def tokenize_eng(text):
    spacy_doc = nlp_spacy(filter_special_tokens(text))
    # append the lemma of the tokes if they are a noun
    tokens = [token.lemma_ for token in spacy_doc if token.pos_ in ['NOUN', 'PROPN']]
    # remove stop-words and replace with synonym if there exists one
    tokens = [replace_with_syn(token) for token in tokens if token.lower() not in nlp_spacy.Defaults.stop_words]
    #combine tokens which belong together ( "x. ray","c. arm" ....)
    tokens = combine_tokens(tokens)
    #filter tokens which are too short or too long
    tokens = [token for token in tokens if len(token)>2 and len(token)<25]
    return tokens

def tokenize_german(text):
    spacy_doc = nlp_spacy_deu(filter_special_tokens(text))
    # append the lemma of the tokes if they are a noun
    tokens = [token.lemma_ for token in spacy_doc if token.pos_ in ['NOUN', 'PROPN']]
    # remove stop-words and replace with synonym if there exists one
    tokens = [replace_with_syn(token) for token in tokens if token.lower() not in nlp_spacy_deu.Defaults.stop_words]
    #combine tokens which belong together ( "x. ray","c. arm" ....)
    tokens = combine_tokens(tokens)
    #filter tokens which are too short or too long
    tokens = [token for token in tokens if len(token)>2 and len(token)<25]
    return tokens

#this method is called in the tokenize method
#to filter special tokens of the transkript like "#ahm", "#cough"
def filter_special_tokens(text):
    tokens = text.split(' ')
    #filter "#ahm".... , wrong spoken words and "ja~deu"
    tokens = [extract_different_lang(token) for token in tokens if "#" not in token and "*" not in token]
    return " ".join(tokens)


def extract_different_lang(word):
    if "~" in word:
        return word[:word.index("~")]
    return word


def combine_tokens(tokens):
    if "c." not in tokens and "x." not in tokens and "s." not in tokens:
        return tokens
    i = 0
    while(i<len(tokens)-1):
        #checks if "c." and "arm" are 2 seperate tokens
        if tokens[i] == "c.":
            if tokens[i+1] == "arm":
                tokens[i] = "c.arm"
                tokens.pop(i+1)
        #checks for "x." and "ray"
        elif tokens[i] == "x.":
            if tokens[i+1] == "ray":
                tokens[i] = "x.ray"
                tokens.pop(i+1)
        #checks for "s","v","d"
        elif tokens[i] == "s.":
            if i+2 >= len(tokens):
                i=i+1
                continue
            if tokens[i+1] == "v." and tokens[i+2] == "d.":
                tokens[i] = "s.v.d."
                tokens.pop(i+2)
                tokens.pop(i+1)
        i = i+1
    return tokens