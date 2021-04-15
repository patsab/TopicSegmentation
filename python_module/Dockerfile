FROM python:3.9.2-buster

#First copy the requirments.txt and load them
#this caches the container and doesnt need to reinstall every dependency
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install -r requirements.txt
RUN python3 -m spacy download en_core_web_trf
RUN python3 -m spacy download de_core_news_lg
#the models are saved in a file
#therefore we create a folder for these files
RUN mkdir -p /app/saved_models

#get the rest of the code
COPY ./local_config.cfg /app/local_config.cfg
COPY ./model_creation.py /app/model_creation.py
COPY ./pre_processing.py /app/pre_processing.py
COPY ./topic_seg.py /app/topic_seg.py


#Start the app as flask dev server
ENTRYPOINT ["python"]
CMD ["/app/topic_seg.py"]
