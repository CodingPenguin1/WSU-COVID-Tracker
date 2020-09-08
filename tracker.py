#!/usr/bin/env python3
import json
import smtplib
import urllib.request
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from os.path import basename

import matplotlib.pyplot as plt
import pandas as pd
from bs4 import BeautifulSoup


def generate_plot(dataframe):
    colors = ['black', 'red', 'blue', 'green', 'orange', 'purple']

    datasets = []
    datasets.append(list(dataframe['dayton_students']))
    datasets.append(list(dataframe['dayton_employees']))
    datasets.append(list(dataframe['lake_students']))
    datasets.append(list(dataframe['lake_employees']))

    dates = list(dataframe['date'])
    dataset_labels = ['Dayton Students', 'Dayton Employees', 'Lake Students', 'Lake Employees']

    fig = plt.figure()
    ax1 = fig.add_subplot(111)

    # Iterate through different datasets
    for i in range(len(datasets)):
        ax1.plot(dates, datasets[i], c=colors[i], label=dataset_labels[i], linestyle='-')

    # plt.xticks([dates[i] for i in range(0, len(dates) + 1, len(dates) // 4)])
    plt.legend(loc='upper left')
    plt.title('Wright State University COVID-19 Cases')

    plt.savefig('plot.png')


def _authenticate(file='credentials.json'):
    with open(file, 'r') as f:
        contents = '\n'.join(f.readlines())
        credentials = json.loads(contents)
        return credentials['email'], credentials['password']


def send_emails():
    # Login
    gmail_user, gmail_password = _authenticate()
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.ehlo()
    server.login(gmail_user, gmail_password)

    # Read list of users to email
    with open('recipients.txt', 'r') as f:
        recipients = [line.strip() for line in f.readlines()]

    for recipient in recipients:
        subject = 'WSU COVID-19 Statistics'

        # Create and send email
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = recipient
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject
        # msg.attach(MIMEText(table))
        with open('plot.png', 'rb') as f:
            part = MIMEApplication(f.read(), Name='plot.png')
        part['Content-Disposition'] = 'attachment; filename="%s' % 'plot.png'
        msg.attach(part)
        print(recipient)
        server.sendmail(gmail_user, recipient, msg.as_string())

    server.close()


if __name__ == '__main__':
    page = urllib.request.urlopen('https://www.wright.edu/coronavirus/covid-19-dashboard')
    soup = BeautifulSoup(page, features='html.parser')
    # print(soup.prettify())

    # Parse table
    tables = soup.find_all('table', attrs={'cellpadding': '1', 'cellspacing': '1'})
    tables_data = []
    for table in tables:
        data = []
        table_body = table.find('tbody')

        rows = table_body.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            data.append([ele for ele in cols if ele])  # Get rid of empty values

        tables_data.append(data)

    current_data = {'date': str(datetime.today().strftime('%d-%m-%Y')),
                    'dayton_students': int(tables_data[0][0][-1]),
                    'dayton_employees': int(tables_data[1][0][-1]),
                    'lake_students': int(tables_data[2][0][-1]),
                    'lake_employees': int(tables_data[3][0][-1])}

    try:
        # Append today's data
        cases_df = pd.read_csv('cases.csv')
        cases_df = cases_df.append(current_data, ignore_index=True)
        cases_df.to_csv('cases.csv', index=False)
    except FileNotFoundError:
        # Initial write
        for key in current_data.keys():
            current_data[key] = [current_data[key]]
        cases_df = pd.DataFrame(current_data)
        cases_df.to_csv('cases.csv', index=False)

    generate_plot(cases_df)

    # Send emails
    send_emails()
