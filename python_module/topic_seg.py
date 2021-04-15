#imports for the flask_functionality
from flask import Flask, jsonify, request
from flask_cors import CORS

#imports for pymongo data managment
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import date,datetime,timedelta

from waitress import serve

import json

import pre_processing as pre_processing
import model_creation as model_creation

from threading import Thread

from gensim.models import LsiModel
from gensim.models import nmf

import os
import sys


#configs and wrappers for flask app 
app = Flask(__name__)
app.config.from_pyfile('local_config.cfg')
CORS(app)
mongo = PyMongo(app)

os.environ["TOKENIZERS_PARALLELISM"] = "false"

modelPath = 'saved_models/'

@app.route('/insert', methods=['POST'])
def insert_new_lecture():
    dataRequest = {}
    try:
        dataRequest = request.get_json(force=True)
    except :
        return jsonify({'error':'Payload is not a valid json object'}),400
    #extract the data from the request and check if values are there
    lectureData = {} 
    #necessary fields
    try: 
        lectureData['lecture'] = dataRequest['lecture']
        lectureData['lecture_key'] = dataRequest['lecture_key']
        lectureData['texts'] = check_timestamps_of_texts(dataRequest['texts'])
        should_update = dataRequest.get('update', True)
        language = dataRequest.get('lang','en')
    except:
        return jsonify({'error':'wrong params'}),400
    #check if lecture already exists
    if get_lecture_from_db(lectureData['lecture']) is not None:
        return jsonify({'error':'lecture already exists'}),400
    #start the preprocessing in a seprate 
    processLecture(lectureData['lecture'],
                    lectureData['lecture_key'],
                    lectureData['texts'],
                    should_update,
                    language)
    return jsonify('Lecture was added')

@app.route('/lectures')
def check_mongo_connection():
    output= []
    lectures = mongo.db.lectures.find()
    for lect in lectures:
        output.append({'lecture': lect['lecture'], 'key':lect['lecture_key']})
    return jsonify({"lectures":output})

@app.route('/keywords', methods=['GET'])
def get_keywords_from_db():
    try:
        lecture_key = request.args['lecture_key']
        modeltype = request.args['model_type']
    except:
        return jsonify({'error': 'lecture_key or model_type is missing'})
    keyword = mongo.db.keywords.find_one({'lecture_key': lecture_key, 'model_type': modeltype})
    if keyword is None:
        return jsonify({'error':'no keywords found'}),400
    return jsonify({'result':keyword['keywords']})

@app.route('/topicdist', methods=['GET'])
def topic_dist():
    #get data form request
    try:
        lecture = request.args['lecture']
        model = request.args.get('model','nmf')
        segment_seg = int(request.args.get('seg_sec',120))
        overlap = int(request.args.get('overlap',30))
    except:
        return jsonify({'error':'wrong params'}),400
    result = calculate_topic_dist(lecture=lecture, model_type=model, segment_seg=segment_seg, overlap=overlap)
    return jsonify({"result": result})


def calculate_topic_dist(lecture, model_type,segment_seg,overlap):
    #get the lecture object from the database
    lecture_obj = get_lecture_from_db(lecture)
    if lecture_obj is None:
        return ''
    #get the used corpus
    corpus_obj = mongo.db.corpus.find_one({'model_name':'{0}_{1}'.format(lecture_obj['lecture_key'], model_type)})
    if corpus_obj is None:
        return ''
    #load the model from file 
    normalize = False
    if model_type == 'nmf':
        model = nmf.Nmf.load('{0}{1}_{2}'.format(modelPath,lecture_obj['lecture_key'],model_type))
    elif model_type == 'lsi':
        model = LsiModel.load('{0}{1}_{2}'.format(modelPath,lecture_obj['lecture_key'],model_type))
        normalize = True
    #the "parts" key contains the individual rows for the segmentation
    #these need to be grouped according to seg_sec and overlap
    rows = lecture_obj['parts']
    segmented_parts = segment_lecture(rows, segment_sec=segment_seg, overlap=overlap)
    #calculate distrib for each segment
    topic_dist = []
    for segment in segmented_parts:
        distrib = model_creation.apply_dataframe_to_model(model,corpus_obj['corpus'],segment['tokens'],normalize)
        topic_dist.append({'distribution':distrib,'time_from':segment['time_from'], 'time_to':segment['time_from']})
    return topic_dist


def get_lecture_from_db(lecture):
    return mongo.db.lectures.find_one({'lecture':lecture})


def processLecture(lecture,lecture_key,texts,update,language='en'):
    #tokenize
    tokenized = tokenize_lectures(lecture, lecture_key,texts,language)
    #save in db
    mongo.db.lectures.insert_one(tokenized)
    #add words to the dictionary for gensim
    #the add_documents function of gensim only supports list of lists of strings. So we need to include the token list in another list
    model_creation.add_words_to_dictionary([tokenized["tokens"]])
    #update models for each lecture of the same key
    if update:
        update_models(tokenized['lecture_key'])


def tokenize_lectures(lecture,lecture_key,texts,language='en'):
    #create the rows Dataframe
    rows = []
    tokens = []
    text_whole = ''
    for text in texts:
        rowObject = {}
        rowObject['text'] = pre_processing.filter_special_tokens(text['text']).replace("\n","")
        rowObject['tokens'] = pre_processing.tokenize(rowObject['text'],language)
        rowObject['time_from'] = text['time_from'] 
        rowObject['time_to'] = text['time_to']
        #if there are no tokens, there is no need to add the row
        if rowObject['tokens']:
            rows.append(rowObject)
            text_whole = text_whole +  rowObject['text'] + ' '
            tokens = tokens + rowObject['tokens']
    return {'lecture':lecture, 'lecture_key':lecture_key ,'text': text_whole, 'tokens': tokens, "parts":rows} 
    

def check_timestamps_of_texts(data):
    #check if the keys are all in there
    for i in data:
        if all (keys in i for keys in ("time_from","time_to","text")):
            continue
        else:
            raise
    return data

#we update the models
#we use traindata = testdata
def update_models(lecture_key):
    #get the token list of coherent lectures
    lectures = get_lectures_with_key(lecture_key);
    token_list = []
    for lect in lectures:
        token_list.append(lect['tokens'])
    best_model_nmf,corpus_nmf = model_creation.get_best_model(token_list= token_list,
                                                min_topic_num=4,
                                                max_topic_num=12,
                                                model_type='nmf')
    best_model_lsi,corpus_lsi = model_creation.get_best_model(token_list= token_list,
                                                min_topic_num=4,
                                                max_topic_num=12, 
                                                model_type='lsi')
    #get model keywords
    nmf_keywords = model_keywords(best_model_nmf)
    lsi_keywords = model_keywords(best_model_lsi)
    #save keywords in database
    store_keywords(nmf_keywords,lecture_key=lecture_key, modeltype="nmf")
    store_keywords(lsi_keywords,lecture_key=lecture_key, modeltype="lsi")
    #save corpus in db
    #usually they are the same, but if u just want to update 1 model or so, it needs to be handeld seperatly
    store_corpus(corpus_nmf,'{0}_nmf'.format(lecture_key))
    store_corpus(corpus_lsi,'{0}_lsi'.format(lecture_key))
    #save models in file
    best_model_lsi.save('{0}{1}_lsi'.format(modelPath,lecture_key))
    best_model_nmf.save('{0}{1}_nmf'.format(modelPath,lecture_key))

def store_keywords(keywords, lecture_key, modeltype):
    if check_existing_keywords(lecture_key,modeltype):
        mongo.db.keywords.update_one({'lecture_key': lecture_key, 'model_type': modeltype},
                                    {"$set":{'keywords':keywords}})
    else:
        mongo.db.keywords.insert_one({'lecture_key': lecture_key, 'model_type': modeltype, 'keywords': keywords})


def check_existing_keywords(lecture_key,modeltype):
    keyword = mongo.db.keywords.find_one({'lecture_key': lecture_key, 'model_type': modeltype})
    if keyword is None:
        return False
    else:
        return True

def store_corpus(corpus,model_name):
    if mongo.db.corpus.find_one({'model_name': model_name}) is None:
        mongo.db.corpus.insert_one({'corpus':corpus, 'model_name': model_name})
    else:
        mongo.db.corpus.update_one({'model_name': model_name},{"$set":{'model_name':model_name}})

#This function prints the top 10 words for each topic from a given model 
def model_keywords(model):
    output = {}
    for i in range(0, model.num_topics):
        keywords = ''
        keywords_dist = model.show_topic(i)
        for word in keywords_dist:
            keywords += word[0] + ' '
        output[str(i)] = keywords
    return output
    #json.dump(output, open( '{0}.json'.format(filename), 'w' ) )


def get_lectures_with_key(lecture_key):
    lectures = mongo.db.lectures.find({'lecture_key': lecture_key})
    output= []
    for lect in lectures:
        output.append(lect)
    return output



#this methods calcules the time, for each part
def getParts(maxDuration,segment_sec = 90, overlap = 30):
    start_at_every_time = segment_sec - overlap
    cur_time= 0
    counter = 0
    timesegments = []
    while cur_time < maxDuration:
        end_time = cur_time + segment_sec if (cur_time+segment_sec <= maxDuration) else maxDuration
        timesegments.append({"counter":counter,"start":cur_time,"end":end_time})
        cur_time += start_at_every_time
        counter += 1
    return timesegments


#there are all the lectures in parts with a timestamp from start to end(of each part)
def segment_lecture(lecture_data,segment_sec=90,overlap=30):
    #['text']['tokens'] ['time_from']['time_to']
    time_to = max([part['time_to'] for part in lecture_data])
    parts_time = getParts(time_to,segment_sec=segment_sec,overlap=overlap)
    segments = []
    for part in parts_time:
        data = getRowforSegment(lecture_data,part)
        if data:
            segments.append(data)
    return segments
    

#get the tokens for a given timeframe
def getRowforSegment(lecture_data,segment):
    #get the rows in the timeframe as an dataframe
    rows = [row for row in lecture_data if row['time_to'] >= segment['start']]
    rows = [row for row in rows if row['time_to'] <= segment['end']]
    if len(rows) == 0 :
        return
    #create a list with the all tokens
    combined_tokens = []
    for row in rows:
        combined_tokens += row['tokens']
    #return the result while combining the metadata
    return {'time_from':min([row['time_from'] for row in rows]),
            'time_to':max([row['time_to'] for row in rows]),
            'tokens':combined_tokens}



if __name__ == "__main__":
    #use waitress server as production server
    #serve(app,host="0.0.0.0",port=5000)
    #If DB runs from Python script (flask dev server), use: 
    app.run(host='0.0.0.0', port=5000)
