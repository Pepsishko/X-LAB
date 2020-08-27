import re
import os
from tinkoff_voicekit_client import ClientSTT
import csv
import datetime
import uuid
import psycopg2
import sys

class Rec():

    def __init__(self,path,phone,DB,st):
        self.pathToFile = path
        self.phoneNumber = phone
        self.DB = True if DB=="y" else False
        self.stage = st
        self.API_KEY = "KEY"
        self.SECRET_KEY = "KEY"
        self.audio_config = {
            "encoding": "LINEAR16",
            "sample_rate_hertz": 8000,
            "num_channels":1
        }

    def recognize(self): # Метод получения значения сообщения

        def checkAnswer(message): # Метод проверки на Положительное или Отрицательное значение
            notAM = ['нет','До свидания']
            aM = ['Говорите','Да','Удобно','Слушаю']
            for answer in aM:
                if re.search(r'(?i)\b{}\b'.format(answer), message) is not None:
                    return 1
            for answer in notAM:
                if re.search(r'(?i)\b{}\b'.format(answer), message) is not None:
                    return 0

        def checkAnswMachine(message): # Метод проверки на Человека и АО
            if (re.search('Автоответчик'.lower(), message.lower())):
                return 0
            else:
                return 1

        def addToDB(result): # Метод добавления данных в БД
            now = datetime.datetime.now()
            try:
                conn = psycopg2.connect(dbname='database', user='postgres',
                                        password=1, host='127.0.0.1',port="5432")
            except:
                print('Не удалось подключится к бд')
                with open('logErr.csv','a',newline='') as csv_file:
                    writer = csv.writer(csv_file, delimiter=',')
                    data = [{'ID':str(uuid.uuid4()),'Error':'Не удалось подключиться к СУБД'}]
                    writer.writerow(data)
                    sys.exit()
            cursor = conn.cursor()

            date = str(now.day) + "/" + str(now.month) + "/" + str(now.year)
            timeD = str(now.hour) + ":" + str(now.minute) + ":" + str(now.second)
            if self.stage == 1:
                cursor.execute('INSERT INTO public."Answers"("Date", "Time", "Result", "Phone", "Duration", "Message")VALUES (\'{0}\', \'{1}\', \'{2}\', \'{3}\', \'{4}\', \'{5}\');'.format(
                    date,timeD,"АО" if result['stage 1'] == 0 else "Человек",self.phoneNumber, float(result['duration']), result['message']))

            if self.stage == 2:
                cursor.execute('INSERT INTO public."Answers"("Date", "Time", "Result", "Phone", "Duration", "Message") VALUES (\'{0}\', \'{1}\', \'{2}\', \'{3}\', \'{4}\', \'{5}\');'.format(
                        date,timeD,
                        "Отрицательно" if result['stage 2'] == 0 else "Положительно",self.phoneNumber, (result['duration']), result['message']))
            conn.commit()


        def addToLogFile(result): #Добавление записей в лог файл
            now = datetime.datetime.now()

            if self.stage == 1:
                data = [{"ID" : str(uuid.uuid4()),"Date" : str(now.day) + "." + str(now.month) + "." + str(now.year),
                      "Time":str(now.hour) + ":" + str(now.minute) + ":" + str(now.second),
                      "Result": "АО" if result['stage 1']==0 else "Человек" ,"Phone": self.phoneNumber,
                      "Duration": result['duration'], "Message": result['message']}]
            elif self.stage == 2:

                data = [{"ID": str(uuid.uuid4()), "Date": str(now.day) + "." + str(now.month) + "." + str(now.year),
                         "Time": str(now.hour) + ":" + str(now.minute) + ":" + str(now.second),
                         "Result": "Отрицательно" if result['stage 2'] == 0 else "Положительно", "Phone": self.phoneNumber,
                         "Duration": result['duration'], "Message": result['message']}]

            with open('log.csv', "a", newline='') as csv_file:
                writer = csv.writer(csv_file, delimiter=',')
                writer.writerow(data)

        client = ClientSTT(self.API_KEY,self.SECRET_KEY)
        response = client.recognize(self.pathToFile, self.audio_config)
        time = float(re.search(r'\d*\.\d*', response[0]['end_time']).group(0))
        recText = response[0]['alternatives'][0]['transcript']
        if ((self.stage == 1) and (self.DB)):
            checkMachine = checkAnswMachine(recText)
            addToDB({"stage 1": checkMachine, "duration": time, "message": recText})
            #os.remove(self.pathToFile)
        elif ((self.stage == 1) and (self.DB==False)):
            checkMachine = checkAnswMachine(recText)
            addToLogFile({"stage 1" : checkMachine ,"duration": time,"message":recText})
            #os.remove(self.pathToFile)
        elif((self.stage == 2) and (self.DB)):
            if (checkAnswMachine(recText) == 0):
                print('Обнаружен автоответчик используйте 1 этап распознования')
            else:
                checkAns = checkAnswer(response[0]['alternatives'][0]['transcript'])
                addToDB({"stage 2": checkAns, "duration": time, "message": recText})
                #os.remove(self.pathToFile)
        elif ((self.stage == 2) and (self.DB==False)):
            if(checkAnswMachine(recText)==0):
                print('Обнаружен автоответчик используйте 1 этап распознования')
            else:
                checkAns = checkAnswer(response[0]['alternatives'][0]['transcript'])
                addToLogFile({"stage 2": checkAns, "duration": time, "message": recText})
                #os.remove(self.pathToFile)

print('Введите путь к .wav файлу:')
pathToFile = input()
while((os.path.isfile(pathToFile))==False):
    print("Файла не существует. Введите путь к существующему файлу:")
    pathToFile = input()
path, ext = os.path.splitext(pathToFile)
while (ext != '.wav'):
    print("Пожалуйста откройте .wav файл:")
    pathToFile = input()
    path, ext = os.path.splitext(pathToFile)

print('Введите номер телефона(Формата 8(800)888-88-88):')
phoneRe = re.compile(r'\d\(\d{3}\)\d{3}\-\d{2}\-\d{2}')
phoneNumber = None
while(phoneNumber == None):
    phoneNumber = input()
    phoneNumber = phoneRe.search(phoneNumber)
    if(phoneNumber==None):
        print("Вы неверно ввели данные номера телефона. Попробуйте еще раз:")
phoneNumber = phoneNumber.group()

print('Хотите ли записать результаты в БД (Y/N):')
flagDB = input()
while((flagDB.lower() != 'y') and (flagDB.lower() != 'n')):
    print("Пожалуйста выберите Y/N:")
    flagDB = input()
    flagDB = flagDB.lower()

print("Этап распознавания (1 или 2):")
stage = input()
while((stage != '1') and (stage != '2')):
    print("Пожалуйста введите 1 или 2")
    stage = input()
stage = int(stage)
reco = Rec(pathToFile,phoneNumber,flagDB,stage)
reco.recognize()
