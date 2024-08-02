# coding:utf-8
import json
import requests
import configparser
import warnings
import pandas as pd
import re
import html
from bs4 import BeautifulSoup


from requests.auth import HTTPBasicAuth

warnings.filterwarnings("ignore")

config = configparser.ConfigParser()
configJira = configparser.ConfigParser()
config.read("config.ini", encoding='utf-8')
configJira.read("configFields.ini", encoding='utf-8')


# СФЕРА параметры
devUser = config["SFERAUSER"]["devUser"]
devPassword = config["SFERAUSER"]["devPassword"]
sferaUrl = config["SFERA"]["sferaUrl"]
sferaUrlLogin = config["SFERA"]["sferaUrlLogin"]
sferaTestCaseUrl = config["SFERA"]["sferaTestCaseUrl"]
sferaTSectionsUrl = config["SFERA"]["sferaTSectionsUrl"]
sferaSprintUrl = config["SFERA"]["sferaSprintUrl"]
sferaUrlSearch = config["SFERA"]["sferaUrlSearch"]
sferaUrlKnowledge = config["SFERA"]["sferaUrlKnowledge"]
sferaUrlKnowledge2 = config["SFERA"]["sferaUrlKnowledge2"]
sferaUrlRelations = config["SFERA"]["sferaUrlRelations"]
sferaUrlEntityViews = config["SFERA"]["sferaUrlEntityViews"]


session = requests.Session()
session.post(sferaUrlLogin, json={"username": devUser, "password": devPassword}, verify=False)

def get_release_tasks(release):
    # Формируем запрос
    query = 'label%20%3D%20%27' + release + '%27&size=1000&page=0&attributesToReturn=checkbox%2Cnumber%2Cname%2CactualSprint%2Cpriority%2Cstatus%2Cassignee%2Cowner%2CdueDate%2Clabel%2CparentNumber%2Ccomponent'
    url = sferaUrlSearch + "?query=" + query
    # Делаем запрос задач по фильтру
    response = session.get(url, verify=False)
    if response.ok != True:
        raise Exception("Error get sprint data " + response)
    return json.loads(response.text)


def get_task_comments(task_number):
    # Формируем запрос
    path = '/attributes/comments?'
    query = 'sort=createDate,desc&size=1000'
    url = sferaUrlEntityViews + task_number + path + query
    # Делаем запрос задач по фильтру
    response = session.get(url, verify=False)
    if response.ok != True:
        raise Exception("Error get sprint data " + response)
    return json.loads(response.text)

def generate_release_html(tasks_df):
    # Генерируем HTML-код
    html_code = tasks_df.to_html(index=False)

    # Декодируем HTML-спецсимволы
    decoded_html = html.unescape(html_code)
    decoded_html = str.replace(decoded_html, '\n', '')
    decoded_html = str.replace(decoded_html, '\\n', '')
    decoded_html = str.replace(decoded_html, '"', '')
    decoded_html = str.replace(decoded_html, "'", '"')
    decoded_html = str.replace(decoded_html, 'class=sfera-link sfera-task sfera-link-style',
                               'class="sfera-link sfera-task sfera-link-style"')
    decoded_html = str.replace(decoded_html, '<table border=1 class=dataframe>',
                               '<table class="MsoNormalTable" border="1" cellspacing="0" cellpadding="0" width="1440" data-widthmode="wide" data-lastwidth="1761px" style="border-collapse: collapse; width: 1761px;" data-rtc-uid="67d29bf0-31c7-4de5-909d-8cea7a11f75f" id="mce_2">')
    return decoded_html


def publication_release_html(html, parentPage, page_name):
    data = {
        "spaceId": "cbbcfa0b-0542-4407-9e49-61c6aa7caf1b",
        "parentCid": parentPage,
        "name": page_name,
        "content": html
    }
    response = session.post(sferaUrlKnowledge2, json=data, verify=False)
    if response.ok != True:
        raise Exception("Error creating story " + response)
    return json.loads(response.text)


def get_prod_versions(file_path):
    prod = pd.read_csv(file_path, header=None, names=['data'])

    def get_service(value):
        lst = str.split(value, ' ')
        return lst[0]

    def get_version(value):
        lst = str.split(value, ' ')
        return lst[-1]

    prod['service'] = prod['data'].map(get_service)
    prod['version'] = prod['data'].map(get_version)
    prod.drop(columns=['data'], inplace=True)
    return prod


def formation_of_lists(tasks, release, prod):
    component_lst = []
    task_directLink_lst = []
    prod_version_lst = []
    task_lst = []
    inventory_changed_lst = []

    counter = 10 # Начальный счетчик макросов на странице
    for task in tasks['content']:
        new_task = task['number']
        if new_task not in task_lst:
            task_lst.append(new_task)

        if 'component' in task:
            for component in task['component']:
                component_name = component['name']
                if component_name not in component_lst:
                    component_lst.append(component['name'])
                    template = f"""
            <p>  <macro class=is-locked data-name=SferaTasks id=SferaTasks-mce_{counter} contenteditable=false    data-rtc-uid=16cce9cf-5572-4a48-a85b-3375c3c8ed6d><macro-parameter data-name=query      data-rtc-uid=d2a03405-badc-4db9-b558-c63defb0c191>label = '{release}' and      component='{component_name}'</macro-parameter><macro-parameter data-name=name      data-rtc-uid=299855c1-a21a-4a91-88b3-99539008e3c6>{release}_{component_name}</macro-parameter><macro-parameter      data-name=maxTasks data-rtc-uid=4a9ba1c3-6e18-4939-a108-7890b7347054>20</macro-parameter><macro-parameter      data-name=attributes      data-rtc-uid=150ff77e-2639-48fa-bba0-32dd06b4104f>[{{'name':'Ключ','code':'number'}},{{'name':'Название','code':'name'}},{{'name':'Статус','code':'status'}},{{'name':'Исполнитель','code':'assignee'}}]</macro-parameter><macro-parameter      data-name=createdDate      data-rtc-uid=05fa3e33-7799-4ddc-bc7e-316a518aeeaa>1716579558662</macro-parameter><macro-parameter      data-name=isLocked      data-rtc-uid=3ba10cb8-4865-45c1-aae9-0e8c5437f9c8>false</macro-parameter><macro-rich-text      data-rtc-uid=5dfe052c-765d-4974-8d5d-4d3e356f9bd9></macro-rich-text></macro></p>
            """
                    counter += 1
                    task_directLink_lst.append(template)
                    matching_rows = prod[prod['service'].str.contains(component_name)]
                    if not matching_rows.empty:
                        version = matching_rows['version'].values[0]
                        prod_version_lst.append(version)
                    else:
                        prod_version_lst.append('')

                    # if component_name in prod['service'].values:
                    #     version = prod.loc[prod['service'] == component_name, 'version'].values[0]
                    #     prod_version_lst.append(version)
                    # else:
                    #     prod_version_lst.append('')
        else:
            print("Нет компоненты: ",task['number'])

        if 'label' in task:
            for label in task['label']:
                if label['name'] == 'ОКР_изменение_инвентори':
                    comments = get_task_comments(new_task)
                    if 'content' in comments:
                        text = 'Изменение инвентори:'
                        for comment in comments['content']:
                            if '#Инвентори' in comment['text']:
                                text = text + '<br>' + comment['text']
                                text = text.replace('#Инвентори', '')
                                text = text.replace('\n', '<br>')
                        inventory_changed_lst.append(text)



    return component_lst, task_directLink_lst, prod_version_lst, task_lst, inventory_changed_lst


def create_df(component_lst, task_directLink_lst, prod_version_lst, new_version, inventory_changed_lst):
    # Проверка на пустоту списка inventory_changed_lst
    if not inventory_changed_lst:
        inventory_changed_lst = [''] * len(component_lst)  # Заполнение пустыми строками, если список пустой

    tasks_df = pd.DataFrame({
        'Сервис': component_lst,
        'Задачи в сфере': task_directLink_lst,
        'Версия поставки Новый цод': new_version,
        'Версия для откатки': prod_version_lst,
        'Требует выкатку связанный сервис': '',
        'Версия еДТО': '',
        'Тест-кейсы': '',
        'БЛОК': '',
        'Изменение инвентари': inventory_changed_lst,
        'Комментарии': ''
    })
    return tasks_df


def generating_release_page(parent_page, release, new_version, for_publication_flg):
    # Загружаем версии ПРОДа
    prod = get_prod_versions('data/prod.csv')

    # загружаем задачи релиза
    tasks = get_release_tasks(release)

    # Обрабатываем запрос, проходя по всем задачам и формируя списки
    component_lst, task_directLink_lst, prod_version_lst, task_lst, inventory_changed_lst = formation_of_lists(tasks, release, prod)

    # Создаем dataframe
    tasks_df = create_df(component_lst, task_directLink_lst, prod_version_lst, new_version, inventory_changed_lst)

    # Формируем HTML таблицу
    html = generate_release_html(tasks_df)

    # Публикуем страницу
    if for_publication_flg:
        publication_release_html(html, parent_page, release)
    return task_lst


def add_task_to_story(task_list,story):
    for task in task_list:
        data = {
        "entityNumber": story,
        "relatedEntityNumber": task,
        "relationType": "associatedbugsandstories"
        }
        response = session.post(sferaUrlRelations, json=data, verify=False)
        # if response.ok != True:
        #     raise Exception("Error creating story " + response)


def createSferaTask(release):
    data = {
        "name": "Релиз " + release,
        "assignee": devUser,
        "owner": devUser,
        "estimation": 86400,
        "remainder": 86400,
        "description": "Релиз " + release,
        "priority": "average",
        "status": "created",
        "type": "story",
        "areaCode": "SKOKR",
        "customFieldsValues": [
            {
                "code": "streamConsumer",
                "value": "Скоринговый конвейер КМБ"
            },
            {
                "code": "streamOwner",
                "value": "Скоринговый конвейер КМБ"
            },
            {
                "code": "projectConsumer",
                "value": "da2bc81b-5928-4f05-a7f4-4a9a5e48ce68"
            },
            {
                "code": "workGroup",
                "value": "Новая функциональность"
            },
            {
                "code": "systems",
                "value": "1864 Скоринговый конвейер кредитования малого бизнеса"
            },
            {
                "code": "changeType",
                "value": "Создание/Доработка ИС"
            },
            {
                "code": "decision",
                "value": "! Нет решения"
            },
            {
                "code": "rightTransferApproval",
                "value": 'true'
            },
            {
                "code": "acceptanceCriteria",
                "value": "Функциональность успешно выведена в ПРОД"
            },
            {
                "code": "artifactsCreateRework",
                "value": "Архитектура ИС"
            },
            {
                "code": "artifactsCreateRework",
                "value": "ПМИ ИС"
            },
            {
                "code": "artifactsCreateRework",
                "value": "Протокол тестирования ИС"
            },
            {
                "code": "artifactsCreateRework",
                "value": "Тестовые планы и сценарии ИС"
            },
            {
                "code": "artifactsCreateRework",
                "value": "Тестовые планы и сценарии Решения"
            },
            {
                "code": "artifactsCreateRework",
                "value": "Требования к ИС"
            },
            {
                "code": "lackLoadTestReason",
                "value": "Решение лидера команды развития"
            },
            {
                "code": "isContractorWork",
                "value": "Не определено"
            }
        ]
    }

    response = session.post(sferaUrlSearch, json=data, verify=False)
    if response.ok != True:
        raise Exception("Error creating story " + response)
    return json.loads(response.text)


# Генерация страницы ЗНИ с QL выборками
# Задаем константы
parent_page = '1295831'
release = 'OKR_20240825_IR' # Метка релиза
new_version = '2403.6.0' # Текущая версия сервиса
story = 'SKOKR-6384'
for_publication_flg = True # Если True - то публикуем, если False, только возврат списка задач

task_lst = generating_release_page(parent_page, release, new_version, for_publication_flg)
if story != '':
    add_task_to_story(task_lst, story)
else:
    story = createSferaTask(release)
    add_task_to_story(task_lst, story)
    print(story)