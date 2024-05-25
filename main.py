# coding:utf-8
import json
import requests
import configparser
import warnings
import pandas as pd
import re
import html


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

# session = requests.Session()
# session.auth = (config["USER"]["user"], config["USER"]["password"])
session = requests.Session()
session.post(sferaUrlLogin, json={"username": devUser, "password": devPassword}, verify=False)


def release_page_gen(parentPage, release, page_name):
    tasks = get_release_tasks(release)
    df = create_release_task_df(tasks)
    grouped_df = create_release_df(df)
    html = generate_release_html(grouped_df)
    publication_release_html(html, parentPage, page_name)


def get_release_tasks(release):
    # Формируем запрос
    query = 'label%20%3D%20%27' + release + '%27&size=1000&page=0&attributesToReturn=checkbox%2Cnumber%2Cname%2CactualSprint%2Cpriority%2Cstatus%2Cassignee%2Cowner%2CdueDate%2Clabel%2CparentNumber%2Ccomponent'
    url = sferaUrl + "?query=" + query
    # Делаем запрос задач по фильтру
    response = session.get(url, verify=False)
    if response.ok != True:
        raise Exception("Error get sprint data " + response)
    return json.loads(response.text)


def create_release_task_df(tasks):
    # Обрабатываем запрос, проходя по всем задачам и формируя списки
    component_lst = []
    task_directLink_lst = []


    for task in tasks['content']:
        for component in task['component']:
            component_lst.append(component['name'])
            # task_directLink_lst.append(task['directLink'])
            task_number = task['number']
            task_name = task['name']
            template = f"""
    <p><a target=_blank href=https://sfera.inno.local/tasks/task/{task_number} contenteditable=false class=sfera-link sfera-task sfera-link-style style=text-decoration: none; data-rtc-uid=40340632-c702-45bb-a461-93fdd7f681ef rel=noopener data-mce-href=https://sfera.inno.local/tasks/task/{task_number} data-mce-contenteditable=false>{task_number} {task_name}<span>&nbsp;</span>Выполнено<button class=sfera-status-button sfera-status-done>Выполнено</button></a></p>
    """
            task_directLink_lst.append(template)

    tasks_df = pd.DataFrame({
        'Сервис': component_lst,
        'Задачи в сфере': task_directLink_lst

    })
    return tasks_df


def create_release_df(df):
    grouped_df = df.groupby('Сервис').agg(lambda x: ', '.join(map(str, x)))
    grouped_df['Требует выкатку связанный сервис'] = ''
    grouped_df['Версия поставки Новый цод'] = ''
    grouped_df['Версия еДТО'] = ''
    grouped_df['Версия для откатки'] = ''
    grouped_df['Тест-кейсы'] = ''
    grouped_df['БЛОК'] = ''
    grouped_df['Комментарии'] = ''
    return grouped_df


def generate_release_html(grouped_df):
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

    counter = 10 # Начальный счетчик макросов на странице
    for task in tasks['content']:
        new_task = task['number']
        if new_task not in task_lst:
            task_lst.append(new_task)
        for component in task['component']:
            component_name = component['name']
            if component_name not in component_lst:
                component_lst.append(component['name'])
                template = f"""
        <p>  <macro class=is-locked data-name=SferaTasks id=SferaTasks-mce_{counter} contenteditable=false    data-rtc-uid=16cce9cf-5572-4a48-a85b-3375c3c8ed6d><macro-parameter data-name=query      data-rtc-uid=d2a03405-badc-4db9-b558-c63defb0c191>label = '{release}' and      component='{component_name}'</macro-parameter><macro-parameter data-name=name      data-rtc-uid=299855c1-a21a-4a91-88b3-99539008e3c6>{release}_{component_name}</macro-parameter><macro-parameter      data-name=maxTasks data-rtc-uid=4a9ba1c3-6e18-4939-a108-7890b7347054>20</macro-parameter><macro-parameter      data-name=attributes      data-rtc-uid=150ff77e-2639-48fa-bba0-32dd06b4104f>[{{'name':'Ключ','code':'number'}},{{'name':'Название','code':'name'}},{{'name':'Статус','code':'status'}},{{'name':'Исполнитель','code':'assignee'}}]</macro-parameter><macro-parameter      data-name=createdDate      data-rtc-uid=05fa3e33-7799-4ddc-bc7e-316a518aeeaa>1716579558662</macro-parameter><macro-parameter      data-name=isLocked      data-rtc-uid=3ba10cb8-4865-45c1-aae9-0e8c5437f9c8>false</macro-parameter><macro-rich-text      data-rtc-uid=5dfe052c-765d-4974-8d5d-4d3e356f9bd9></macro-rich-text></macro></p>
        """
                counter += 1
                task_directLink_lst.append(template)
                if component_name in prod['service'].values:
                    version = prod.loc[prod['service'] == component_name, 'version'].values[0]
                    prod_version_lst.append(version)
                else:
                    prod_version_lst.append('')

    return component_lst, task_directLink_lst, prod_version_lst, task_lst


def create_df(component_lst, task_directLink_lst, prod_version_lst, new_version):
    tasks_df = pd.DataFrame({
        'Сервис': component_lst,
        'Задачи в сфере': task_directLink_lst,
        'Версия поставки Новый цод': new_version,
        'Версия для откатки': prod_version_lst,
        'Требует выкатку связанный сервис': '',
        'Версия еДТО': '',
        'Тест-кейсы': '',
        'БЛОК': '',
        'Комментарии': ''
    })
    return tasks_df


# # Генерация страницы ЗНИ
# parent_page = '426943'
# release = 'OKR_20240623_ATM'
# release_page_gen(parent_page, release, release)


# Генерация страницы ЗНИ с QL выборками
# Задаем константы
parent_page = '426943'
release = 'OKR_20240623_ATM' # Метка релиза
service = 'skmb-pledge-adapter' # Метка сервиса
new_version = '2402.5.0' # Текущая версия сервиса
story = ''

# Загружаем версии ПРОДа
prod = get_prod_versions('data/prod.csv')

# загружаем задачи релиза
tasks = get_release_tasks(release)

# Обрабатываем запрос, проходя по всем задачам и формируя списки
component_lst, task_directLink_lst, prod_version_lst, task_lst = formation_of_lists(tasks, release, prod)

# Создаем dataframe
tasks_df = create_df(component_lst, task_directLink_lst, prod_version_lst, new_version)

# Формируем HTML таблицу
html = generate_release_html(tasks_df)

# Публикуем страницу
result = publication_release_html(html, parent_page, release)
print(result)