import xmltodict
import xlwt
import traceback
import numpy as np
import pandas as pd
from time import gmtime, strftime
import argparse
import json
import re
from functools import reduce


__author__ = "Daniel Osorio"
__credits__ = ["Daniel Osorio"]
__version__ = "1.0.0"
__maintainer__ = "Daniel Osorio"
__email__ = "vdosavh@gmail.com"
__status__ = "Production"

class GEMuseXMLReader:
    def __init__(self, path):
        try:
            with open(path) as fd:
                self.dic = xmltodict.parse(fd.read())
            self.__path = path
            self.__patientInfoNode = self.dic['sapphire']['dcarRecord']['patientInfo']
            self.__ecgNode = self.__patientInfoNode['visit']['order']['ecgResting']['params']['ecg']['wav']['ecgWaveformMXG']
            self.header = self.__makeHeaderDic()
            self.__makeDataArray()
            self.__makeStructuredArray()

        except Exception: 
            print(traceback.print_exc())

    
    def __makeHeaderDic(self):
        patientInfo = self.__patientInfoHeader()
        deviceInfo = self.__deviceInfoHeader()
        acquisitionInfo = self.__aquisitionInfoHeader()
        return {'PatientInfo': patientInfo, 'DeviceInfo': deviceInfo, 'AcquisitionInfo': acquisitionInfo}


    def __patientInfoHeader(self):
        if(self.__patientInfoNode['unknownID']['@V']!="true"):
            given_name = self.__patientInfoNode['name']['given']['@V']
            family_name = self.__patientInfoNode['name']['family']['@V']
            id = self.__patientInfoNode['identifier']['id']['@V']
        else:
            given_name = 'Unknown'
            family_name = 'Unknown'
            id = 'Unknown'
        gender = self.__patientInfoNode['gender']['@V']
        race = self.__patientInfoNode['raceCode']['@V']
        pacemaker = self.__patientInfoNode['visit']['order']['testInfo']['hasPacemaker']['@V']
        return {'Given_Name': given_name, 'Family_Name': family_name, 'ID': id, 'Gender': gender, 'Race': race, 'Pacemaker': pacemaker}

    
    def __deviceInfoHeader(self):
        deviceModel = self.__patientInfoNode['visit']['order']['device']['modelID']['@V']
        deviceName = self.__patientInfoNode['visit']['order']['device']['deviceName']['@V']
        deviceSerial = self.__patientInfoNode['visit']['order']['device']['serialID']['@V']
        return {'DeviceModel': deviceModel, 'DeviceName': deviceName, 'DeviceSerial': deviceSerial}

    
    def __aquisitionInfoHeader(self):
        acquisitionDate = self.__patientInfoNode['visit']['order']['testInfo']['acquisitionDateTime']['@V']
        LeadAmplitudeUnitsPerBit = self.__ecgNode['@S']
        LeadAmplitudeUnits = self.__ecgNode['@U']
        Res = self.__ecgNode['@INV']
        filters = self.__getFilterInfo()
        sampleRate = {'SampleRate': self.__ecgNode['sampleRate']['@V'], 'Units': self.__ecgNode['sampleRate']['@U']}
        leadsInformation = self.__getLeadInfo()
        return {'Resolution': Res, 'AcquisitionDate': acquisitionDate, 'LeadAmplitudeUnitsPerBit': LeadAmplitudeUnitsPerBit, 'LeadAmplitudeUnits': LeadAmplitudeUnits, 'Filters': filters, 'SampleRate': sampleRate, 'LeadsInformation': leadsInformation}

    
    def __getFilterInfo(self):
        highPassNode = self.__ecgNode['filters']['highPass']
        highPass = {'Frequency': highPassNode['frequency']['@V'], 'Units': highPassNode['frequency']['@U'], 'Order': highPassNode['order']['@V']}
        LowPassNode = self.__ecgNode['filters']['lowPass']
        lowPass = {'Frequency': LowPassNode['frequency']['@V'], 'Units': LowPassNode['frequency']['@U'], 'Order': LowPassNode['order']['@V']}
        algorithms = []
        algorithmsNodes = self.__ecgNode['filters']['algorithm']
        for i in algorithmsNodes:
            algorithms.append({'Name': i['name']['@V'], 'Purpose': i['purpose']['@V']})
        return {'HighPass': highPass, 'LowPass': lowPass, 'Algorithms': algorithms}


    def __getLeadInfo(self):
        leadsNames = []
        leadsLabels = []
        for i in self.__ecgNode['ecgWaveform']:
            leadsNames.append(i['@lead'])
            leadsLabels.append(i['@label'])
            self.__numberOfSamples = i['@asizeVT']
        self.__leadsNames = leadsNames
        return {'LeadsNames': leadsNames, 'LeadsLabels': leadsLabels, 'NumberOfSamples': self.__numberOfSamples}


    def __makeDataArray(self):
        self.dataArray = np.zeros((int(self.__numberOfSamples), len(self.__leadsNames)), dtype=int)
        for i in range(0, len(self.__ecgNode['ecgWaveform'])):
            self.dataArray[:, i] = list(map(int, self.__ecgNode['ecgWaveform'][i]['@V'].split(' ')))


    def __makeStructuredArray(self):
        self.dataObject = {}
        for i in range(0, len(self.__ecgNode['ecgWaveform'])):
            self.dataObject[self.__leadsNames[i]] = self.dataArray[:, i]
        
        self.dataFrame = pd.DataFrame(self.dataObject)
        
        self.__data_string = self.dataFrame.to_string(header=False)
        self.__data_string = re.sub(' +',',', self.__data_string)
        self.__header_string = 'nSeq '
        self.__header_string += reduce((lambda x, y: x + ' ' + y), self.__leadsNames)

        self.header['AcquisitionInfo']['HeaderString'] = self.__header_string

    def getLead(self, lead):
        return self.dataFrame[[lead]]


    def __makeOSHeader(self):
        self.__OSHeader = {'00:00:00:00:00:00': {}}
        self.__OSHeader['00:00:00:00:00:00']['sensor'] = ['RAW'] * len(self.__ecgNode['ecgWaveform'])
        self.__OSHeader['00:00:00:00:00:00']['device name'] = self.header['DeviceInfo']['DeviceName']
        self.__OSHeader['00:00:00:00:00:00']['column'] = self.__header_string.split(' ')
        self.__OSHeader['00:00:00:00:00:00']['sync interval'] = 0
        self.__OSHeader['00:00:00:00:00:00']['time'] = (self.header['AcquisitionInfo']['AcquisitionDate'].split('T')[1]+'0').strip()
        self.__OSHeader['00:00:00:00:00:00']['date'] = (self.header['AcquisitionInfo']['AcquisitionDate'].split('T')[0]).strip()
        self.__OSHeader['00:00:00:00:00:00']['comments'] = ''
        self.__OSHeader['00:00:00:00:00:00']['device connection'] = 'BTH00:00:00:00:00:00'
        self.__OSHeader['00:00:00:00:00:00']['channels'] = list(range(1, 1+len(self.__ecgNode['ecgWaveform'])))
        self.__OSHeader['00:00:00:00:00:00']['mode'] = 0
        self.__OSHeader['00:00:00:00:00:00']['digital IO'] = []
        self.__OSHeader['00:00:00:00:00:00']['firmware version'] = 770
        self.__OSHeader['00:00:00:00:00:00']['device'] = 'virtual_plux'
        self.__OSHeader['00:00:00:00:00:00']['position'] = 0
        self.__OSHeader['00:00:00:00:00:00']['sampling rate'] = int(self.header['AcquisitionInfo']['SampleRate']['SampleRate'])
        self.__OSHeader['00:00:00:00:00:00']['label'] = self.__leadsNames
        self.__OSHeader['00:00:00:00:00:00']['resolution'] = [int(self.header['AcquisitionInfo']['Resolution']).bit_length()] * len(self.__ecgNode['ecgWaveform'])
        self.__OSHeader['00:00:00:00:00:00']['special'] = [{}, {}, {}, {}, {}]
        return json.dumps(self.__OSHeader)

    def saveHeader(self, filename):
        temp = open('./'+ filename + '_header.json', 'w')
        temp.write(json.dumps(self.header))
        temp.close()


    def saveToCSV(self, filename=None):
        if(filename==None):
            filename = 'GEMuseXML'+ strftime("%Y-%m-%d_%H:%M:%S", gmtime())
        temp = open('./'+ filename + '.csv', 'w')
        temp.write('# ' + self.__header_string + '\n')
        temp.write(self.__data_string)
        temp.close()
    

    def saveToPandasCSV(self, filename=None, header=True):
        if(filename==None):
            filename = 'GEMuseXML'+ strftime("%Y-%m-%d_%H:%M:%S", gmtime())
        self.dataFrame.to_csv('./'+ filename + '_pandas.csv')
        if(header):
            self.saveHeader(filename)


    def saveToJson(self, filename=None, header=True):
        if(filename==None):
            filename = 'GEMuseXML' + strftime("%Y-%m-%d_%H:%M:%S", gmtime())
        tempDic = {'Header': self.header, 'Data': {}}
        for i in range(0, len(self.__ecgNode['ecgWaveform'])):
            tempDic['Data'][self.__ecgNode['ecgWaveform'][i]['@lead']] = list(map(int, self.__ecgNode['ecgWaveform'][i]['@V'].split(' ')))
        temp = open('./'+ filename + '.json', 'w')
        temp.write(json.dumps(tempDic))
        temp.close()

    
    def saveToExcel(self, filename=None, header=True):
        if(filename==None):
            filename = 'GEMuseXML'+ strftime("%Y-%m-%d_%H:%M:%S", gmtime())
        self.dataFrame.to_excel('./'+ filename + '.xls')
        if(header):
            self.saveHeader(filename)
    

    def saveNumpyArray(self, filename=None, header=True):
        if(filename==None):
            filename = 'GEMuseXML'+ strftime("%Y-%m-%d_%H:%M:%S", gmtime())
        np.save('./'+ filename + '.npy', self.dataArray)
        if(header):
            self.saveHeader(filename)


    def saveToOPS(self, filename=None):
        if(filename==None):
            filename = 'GEMuseXML'+ strftime("%Y-%m-%d_%H:%M:%S", gmtime())
        temp = open('./'+ filename + '.txt', 'w')
        temp.write('# OpenSignals Text File Format\n')
        temp.write('# ' + self.__makeOSHeader() + '\n')
        temp.write('# EndOfHeaders\n')
        temp.write(self.dataFrame.to_string(header=False))
        temp.close()


if __name__ == "__main__":

    def parseArgParser(file, arg, type):
        if(arg == ' '):
            filename = None
        else:
            filename = arg

        if(type == 'csv'):
            file.saveToCSV(filename)
        if(type == 'pcsv'):
            file.saveToPandasCSV(filename)
        elif(type == 'ops'):
            file.saveToOPS(filename)
        elif(type == 'json'):
            file.saveToJson(filename)
        elif(type == 'excel'):
            file.saveToExcel(filename)
        elif(type == 'numpy'):
            file.saveNumpyArray(filename)
        elif(type == 'all'):
            file.saveToCSV(filename)
            file.saveToPandasCSV(filename, False)
            file.saveToOPS(filename)
            file.saveToJson(filename, False)
            file.saveToExcel(filename, False)
            file.saveNumpyArray(filename)


    parser = argparse.ArgumentParser()
    parser.add_argument('file', help="file path")
    parser.add_argument("-csv", help="convert to csv", nargs='?', const=' ')
    parser.add_argument("-pcsv", help="convert to pandas csv", nargs='?', const=' ')
    parser.add_argument("-ops", help="convert to opensignals formated txt", nargs='?', const=' ')
    parser.add_argument("-x", '--excel', help="convert to excel", nargs='?', const=' ')
    parser.add_argument("-np", '--numpy', help="convert to numpy", nargs='?', const=' ')
    parser.add_argument("-json", help="convert to json", nargs='?', const=' ')
    parser.add_argument("-all", help="convert to csv, excel, numpy and json", nargs='?', const=' ')
    args = parser.parse_args()

    file = GEMuseXMLReader(args.file)

    if args.csv:
        parseArgParser(file, args.csv, 'csv')
    
    if args.pcsv:
        parseArgParser(file, args.pcsv, 'pcsv')

    if args.ops:
        parseArgParser(file, args.ops, 'ops')
    
    if args.excel:
        parseArgParser(file, args.excel, 'excel')

    if args.numpy:
        parseArgParser(file, args.numpy, 'numpy')

    if args.json:
        parseArgParser(file, args.json, 'json')

    if args.all:
        parseArgParser(file, args.all, 'all')

    


