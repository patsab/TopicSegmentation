var ctx = document.getElementById('myChart');
var vid = document.getElementById('myVideo');
var table = document.getElementById('myTable');
var lecturename = document.getElementById('lecturename');

var lecture;
var modelSelected;

var topicsFilename;
var topicsDistribFile;
var videofile;

var labels = [];
var datasets = []// contains label, data and backgroundColor

var topicDistribsValues;
var topicKeywordValues;
var topicCount;

var lastUpdated=0;
var lastData = [];

let backgroundColors = ['rgba(0,0,200,0.2)','rgba(200,0,0,0.2)','rgba(0,200,0,0.2)']


//options for the chart
const options = {
    scale: {
        ticks: {
            suggestedMax: 1,
            suggestedMin: 0
        }
    }
};

//init the radar chart in the beginning
var radarChart = new Chart(ctx,{
    type:'radar',
    options:options
})

//read the topic distribution and get the right time
function getDataForTime(seconds){
    let dataPoints = matchTimefromArray(seconds)
    let result = []
    for (var i = 0; i < dataPoints.length; i++) {
        let dataName = `From: ${convertSecToMin(dataPoints[i]['Time_from'])}, To: ${convertSecToMin(dataPoints[i]['Time_to'])}`
        let data = normalizeTopicDist(dataPoints[i]["Topic_dist"])
        result.push({'label': dataName, 'data': data, 'backgroundColor': backgroundColors[i]})
    }
    return result
}

//the nmf model skip output for some topics, these need to be filled with 0s 
function normalizeTopicDist(data){
    dataArray=[]
    for(var i = 0; i < topicCount; i++) {
        let res =  data[i] || 0
        dataArray.push(res)
    }
    return dataArray
}



// get the relevant rows for the data visualization
function matchTimefromArray(seconds){
    let result = [];
    for (var i = 0; i < topicDistribsValues.length; i++) {
        currentTimeslot = topicDistribsValues[i];
        //values need to be beetween the start time (time_from) and the end time (time)_to
        if(currentTimeslot['Time_from'] <= seconds && currentTimeslot['Time_to'] >= seconds){
            result.push(currentTimeslot)
        }
        // the timeslots are in order, so if there is a timeslot which has a higher starting time than the value
        // it means that there are no more values which are in there
        if(currentTimeslot['Time_from'] > seconds){
            break;
        }
    }
    return result
}

function init(){
    // get the lectureName out of the query params of the url
    let queryParams = new URLSearchParams(window.location.search);
    lecture = queryParams.has('lecture') ? queryParams.get('lecture') : '' ;
    // check if lecture is valid 
    lecture = lecturelist.includes(lecture) ? lecture : '';
    // load the topics-file and add the eventListener
    model = queryParams.has('model') ? queryParams.get('model') : 'nmf_120_30';
    if (lecture){
        changeModelType(model);
        //update video source 
        vid.getElementsByTagName('source')[0].setAttribute('src',videofile)
        vid.load();
        // the timeupdate event triggers multiple times a second
        // since this is quite long, we just check every 1,5sec for current video time
        var updateChartInterval = setInterval(function(){
            updateChart()
        },1200);

    }else{
        ctx.style.display = "none";
        vid.style.display = "none";
        table.style.display = "none";
    }
    addElementsToSelection();
}

//reads a local text file, which is usefull for reading the topic data
function readTextFile(file)
{
    var rawFile = new XMLHttpRequest();
    var text = ''
    rawFile.open("GET", file, false);
    rawFile.onreadystatechange = function (){
        if(rawFile.readyState === 4){
            if(rawFile.status === 200 || rawFile.status == 0){
                text =  rawFile.responseText;
            }
        }
    }
    rawFile.send(null);
    return text;
}

function convertSecToMin(time){
    let mins = Math.floor(time/60);
    time = Math.floor(time-(mins*60));
    if(time <= 9){
        time= '0' + time
    }
    return `${mins}:${time}`
}

//pushes the new data into the chart
function updateChart(){
    //if the time didnt changed (video stopped etc) there is no need to update 
    if(vid.currentTime == lastUpdated){
        return
    }
    lastUpdated= vid.currentTime
    let currentData = getDataForTime(lastUpdated)
    //if the data didnt changed, we dont need to update 
    // since the data is used in the chart js chart, it has metadata which means we cant directly compare with ===
    if(currentData.length === lastData.length && currentData.length>0){
         if(currentData[0]['label']==lastData[0]['label']){
            return
        }
    }
    lastData = currentData;
    radarChart.data.datasets = lastData; 
    radarChart.update();
}

function initTopicTable(){
    // read the values keywords from the file
    topicKeywordValues = JSON.parse(readTextFile(topicsFilename));
    // create each topic in the keyword table
    for(var key of Object.keys(topicKeywordValues)){
        let tablerow = table.insertRow(-1)
        let element = document.createElement('td')
        element.innerHTML = 'Topic ' + key
        tablerow.appendChild(element)
        
        element = document.createElement('td')
        element.innerHTML = topicKeywordValues[key]
        tablerow.appendChild(element)
    }
    // set the topicCount
    topicCount = Object.keys(topicKeywordValues).length
}

function createLabels(){
    let i = 0;
    while (i<topicCount){
        labels.push('Topic ' + i);
        i++;
    }
}

function changeModelType(modeltyp){
    modeltyp = modellist.includes(modeltyp) ? modeltyp : 'nmf_120_30';
    modelSelected = modeltyp; 
    let config = modeltyp.split('_')
    let modelT = config[0];
    let seg_sec = config[1];
    let overlap = config[2];
    setFilenamesForModels(lecture=lecture,modeltyp=modelT,seg_sec=seg_sec,overlap=overlap)
    //read the topickeywords and update table in html
    initTopicTable();
    //create the labels for the radar chart
    createLabels();
    //init the Chart
    radarChart.data.labels=labels;
    //read the topic distribFiles
    topicDistribsValues = JSON.parse(readTextFile(topicsDistribFile));  
    //get the current data
    getDataForTime(0);

    updateChart();
}


// updates the keyword file, the distribution file, the videosource and the heading
function setFilenamesForModels(lecture,modeltyp,seg_sec, overlap){
    topicsFilename = `..\\model_keywords\\${lecture}_${modeltyp}_keywords.json`
    topicsDistribFile = `..\\model_distrib\\${lecture}_${modeltyp}_${seg_sec}_${overlap}.json`
    videofile = `..\\LMELectures\\video\\${lecture}.mov`
    lecturename.innerHTML = `${lecture} - ${modeltyp.toUpperCase()}, Segment: ${seg_sec}sec , Overlap: ${overlap}sec` 
}

//takes the elements form the lecturelist and modellist and appends them to the selector in the html
function addElementsToSelection(){
    //add Elements to the lecturlist
    let selectList = document.getElementById('lectursel');
    for (var i = 0; i < lecturelist.length; i++) {
        let option = document.createElement("option");
        let text = lecturelist[i].split('-');
        option.text = `prof: ${text[1]}, lecture: ${text[2]}`;
        option.value = lecturelist[i];
        selectList.appendChild(option);
    }
    //add Elements to the Modellist
    selectList = document.getElementById('modelsel');
    for (var i = 0; i < modellist.length; i++) {
        let option = document.createElement("option");
        let text = modellist[i].split('_')
        option.text = `Model: ${text[0].toUpperCase()}, Segment: ${text[1]}sec , Overlap: ${text[2]}sec`;
        option.value = modellist[i];
        selectList.appendChild(option);
    }
}


function changeLectureAndModel(){
    let lectureSelec = document.getElementById('lectursel').value
    let modelSelec = document.getElementById('modelsel').value

    // both values are selected
    if(lecturelist.includes(lectureSelec) && modellist.includes(modelSelec)){
        //if lecture and model didnt change, then dont redirect
        if (lectureSelec != lecture || modelSelec != modelSelected){
            redirectWithNewModel(lectureSelec,modelSelec)
        }
    }
    // only lecture is selected
    else if(lecturelist.includes(lectureSelec) && lectureSelec != lecture){
        redirectWithNewModel(lectureSelec,"")
    }
    // only model is selected
    else if(modellist.includes(modelSelec) && modelSelec != modelSelected && lecture != ''){
        redirectWithNewModel(lecture,modelSelec)
    }
    //nothing is selected or nothing has changed
    //so do nothing
}

function redirectWithNewModel(lectureNew, modelNew){
    let newUrl = `${window.location.protocol}//${window.location.host}${window.location.pathname}?lecture=${lectureNew}&model=${modelNew}`
    window.location.href = newUrl;
}


//list with all viable lecture names
const lecturelist = [
    '20090427-Hornegger-IMIP01',
    '20090427-Hornegger-PA01', 
    '20090428-Hornegger-IMIP02', 
    '20090428-Hornegger-PA02', 
    '20090504-Hornegger-IMIP03', 
    '20090504-Hornegger-PA03', 
    '20090505-Hornegger-PA04', 
    '20090511-Hornegger-IMIP05', 
    '20090511-Hornegger-PA05', 
    '20090512-Hornegger-IMIP06', 
    '20090512-Hornegger-PA06', 
    '20090518-Hornegger-PA07', 
    '20090519-Hornegger-IMIP08', 
    '20090519-Hornegger-PA08', 
    '20090525-Hornegger-IMIP09', 
    '20090525-Hornegger-PA09', 
    '20090526-Hornegger-IMIP10', 
    '20090609-Hornegger-IMIP12', 
    '20090615-Hornegger-IMIP13', 
    '20090615-Hornegger-PA13', 
    '20090616-Hornegger-IMIP14', 
    '20090616-Hornegger-PA14', 
    '20090623-Hornegger-IMIP16', 
    '20090623-Hornegger-PA15', 
    '20090629-Hornegger-IMIP17', 
    '20090630-Hornegger-IMIP18', 
    '20090630-Hornegger-PA17', 
    '20090706-Hornegger-PA18', 
    '20090707-Hornegger-IMIP20', 
    '20090707-Hornegger-PA19', 
    '20090713-Hornegger-IMIP21', 
    '20090713-Hornegger-PA20', 
    '20090720-Hornegger-IMIP22', 
    '20090720-Hornegger-PA21', 
    '20090720-Hornegger-PA22', 
    '20090721-Hornegger-IMIP23']

const modellist = [
    'lsi_60_0',
    'lsi_60_30',
    'lsi_90_0',
    'lsi_90_30',
    'lsi_120_0',
    'lsi_120_30',
    'nmf_60_0',
    'nmf_60_30',
    'nmf_90_0',
    'nmf_90_30',
    'nmf_120_0',
    'nmf_120_30']

init()