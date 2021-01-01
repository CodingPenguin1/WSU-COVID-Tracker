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
    def convert_to_active_cases(weeks):
        # Active cases are the sum of confirmed and self-reported cases across both campuses for the current week plus the previous two weeks.
        active_cases = []
        for i in range(2, len(weeks)):
            active_cases.append(weeks[i] + weeks[i - 1] + weeks[i - 2])
        return active_cases

    colors = ['black', 'red', 'blue', 'green', 'orange', 'purple']

    datasets = []
    # datasets.append(list(dataframe['dayton_students']))
    datasets.append(convert_to_active_cases(dataframe['dayton_students']))
    datasets.append(convert_to_active_cases(dataframe['dayton_employees']))
    datasets.append(convert_to_active_cases(dataframe['lake_students']))
    datasets.append(convert_to_active_cases(dataframe['lake_employees']))

    dates = list(dataframe['date'])[2:]

    dataset_labels = ['Dayton Students', 'Dayton Employees', 'Lake Students', 'Lake Employees']

    fig = plt.figure()
    ax1 = fig.add_subplot(111)

    # Iterate through different datasets
    for i in range(len(datasets)):
        ax1.plot(dates, datasets[i], c=colors[i], label=dataset_labels[i], linestyle='-')

    # plt.xticks([dates[i] for i in range(0, len(dates) + 1, len(dates) // 4)])
    cleaned_dates = []
    [cleaned_dates.append(x) for x in dates if x not in cleaned_dates]
    dates = cleaned_dates.copy()
    plt.xticks([dates[i] for i in range(0, len(dates), len(dates) // 4)])
    plt.legend(loc='upper left')
    plt.title('Active Wright State University COVID-19 Cases')

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


def format_date(date):
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

    month_day = date[:date.find('–')]
    month = months.index(month_day[:month_day.find(' ')]) + 1
    day = month_day[-2:].strip()
    year = date[date.rfind(', ') + 1:].strip()

    return f'{day}-{month}-{year}'


if __name__ == '__main__':
    page = urllib.request.urlopen('https://www.wright.edu/coronavirus/covid-19-dashboard')
    soup = BeautifulSoup(page, features='html.parser')
    # print(soup.prettify())

    # Parse tables
    tables = soup.find_all('table', attrs={'cellpadding': '1', 'cellspacing': '1'})
    columns = ['date', 'dayton_students', 'dayton_employees', 'lake_students', 'lake_employees']
    data = []
    for table_num, table in enumerate(tables):
        table_body = table.find('tbody')

        rows = table_body.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if str(cols[0]) != '<td><strong>Totals</strong></td>':
                date = format_date(str(cols[0]).strip('</td>\np'))
                # Check if date not in data
                if not any(date in i for i in data):
                    # If so, make new row
                    data.append([date, 0, 0, 0, 0])

                # Append data
                for i in range(len(data)):
                    if data[i][0] == date:
                        confirmed = int(str(cols[1]).replace('strong>', '').strip('<>/td'))
                        self_reported = int(str(cols[2]).replace('strong>', '').strip('<>/td'))
                        data[i][table_num + 1] = confirmed + self_reported
    data.reverse()

    dataframe = pd.DataFrame(data, columns=columns)
    dataframe.to_csv('cases.csv', index=False)

    generate_plot(dataframe)

    # Send emails
    send_emails()
