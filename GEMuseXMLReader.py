import xmltodict
import xlwt
import traceback
import numpy as np
import pandas as pd
from time import gmtime, strftime
import argparse


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
        given_name = self.__patientInfoNode['name']['given']['@V']
        family_name = self.__patientInfoNode['name']['family']['@V']
        id = self.__patientInfoNode['identifier']['id']['@V']
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
        filters = self.__getFilterInfo()
        sampleRate = {'SampleRate': self.__ecgNode['sampleRate']['@V'], 'Units': self.__ecgNode['sampleRate']['@U']}
        leadsInformation = self.__getLeadInfo()
        return {'AcquisitionDate': acquisitionDate, 'LeadAmplitudeUnitsPerBit': LeadAmplitudeUnitsPerBit, 'LeadAmplitudeUnits': LeadAmplitudeUnits, 'Filters': filters, 'SampleRate': sampleRate, 'LeadsInformation': leadsInformation}

    
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
        self.dicionary = {}
        for i in range(0, len(self.__ecgNode['ecgWaveform'])):
            self.dicionary[self.__leadsNames[i]] = self.dataArray[:, i]
        self.structuredArray = pd.DataFrame(self.dicionary)
        

    def saveToCSV(self, filename=None):
        if(filename==None):
            self.structuredArray.to_csv('./GEMuseXML'+ strftime("%Y-%m-%d_%H:%M:%S", gmtime()) + '.csv')
        else:
            self.structuredArray.to_csv('./'+ filename + '.csv')


    def saveToJson(self, filename=None):
        if(filename==None):
            self.structuredArray.to_json('./GEMuseXML'+ strftime("%Y-%m-%d_%H:%M:%S", gmtime()) + '.json')
        else:
            self.structuredArray.to_json('./'+ filename + '.json')

    
    def saveToExcel(self, filename=None):
        if(filename==None):
            self.structuredArray.to_excel('./GEMuseXML'+ strftime("%Y-%m-%d_%H:%M:%S", gmtime()) + '.xls')
        else:
            self.structuredArray.to_excel('./'+ filename + '.xls')

    
    def saveNumpyArray(self, filename=None):
        if(filename==None):
            np.save('./GEMuseXML'+ strftime("%Y-%m-%d_%H:%M:%S", gmtime()) + '.npy', self.dataArray)
        else:
            np.save('./'+ filename + '.npy', self.dataArray)
            

if __name__ == "__main__":

    def parseArgParser(file, arg, type):
        if(arg == ' '):
            filename = None
        else:
            filename = arg

        if(type == 'csv'):
            file.saveToCSV(filename)
        elif(type == 'json'):
            file.saveToJson(filename)
        elif(type == 'excel'):
            file.saveToExcel(filename)
        elif(type == 'numpy'):
            file.saveNumpyArray(filename)
        elif(type == 'all'):
            file.saveToCSV(filename)
            file.saveToJson(filename)
            file.saveToExcel(filename)
            file.saveNumpyArray(filename)


    parser = argparse.ArgumentParser()
    parser.add_argument('file', help="file path")
    parser.add_argument("-csv", help="convert to csv", nargs='?', const=' ')
    parser.add_argument("-x", '--excel', help="convert to excel", nargs='?', const=' ')
    parser.add_argument("-np", '--numpy', help="convert to numpy", nargs='?', const=' ')
    parser.add_argument("-json", help="convert to json", nargs='?', const=' ')
    parser.add_argument("-all", help="convert to csv, excel, numpy and json", nargs='?', const=' ')
    args = parser.parse_args()

    file = GEMuseXMLReader(args.file)

    if args.csv:
        parseArgParser(file, args.csv, 'csv')
    
    if args.excel:
        parseArgParser(file, args.excel, 'excel')

    if args.numpy:
        parseArgParser(file, args.numpy, 'numpy')

    if args.json:
        parseArgParser(file, args.json, 'json')

    if args.all:
        parseArgParser(file, args.all, 'all')

    


