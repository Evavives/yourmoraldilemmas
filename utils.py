import requests
from bs4 import BeautifulSoup
import trafilatura
import re
from email.utils import parsedate_tz, mktime_tz, formatdate
from pathlib import Path
import os
import threading
import pandas as pd

# Paths
dataset_path = Path("google_alerts")
csv_file_path = "alertlinks"
info_csv_path = Path("info.csv")
txt_files_path = Path("texts")
data_path = Path("data")

sender = '"Google Alerts"'

def extract_data_trafi(url):
    """Extracts relevant data from a web page using the Trafilatura library.
    So efficient and nice, but I don't know if it does msitakes...
    Args:
        url (str): The URL of the web page to extract the data from.
    Returns:
        str: The extracted content of the web page.
        str: The title of the web page.
    """
    downloaded = trafilatura.fetch_url(url)
    content = trafilatura.extract(downloaded)
    if content is None:
        return None, None
    title = content[:30]
    return content, title


def get_html_content(url):
    """Gets the content of a web page given its URL.
    Args:
        url (str): The URL of the web page."""
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        return None
    
def extract_title(html_content):
    """Extracts the title of a web page given its HTML content.
    Args:
        html_content (str): The HTML content of the web page."""
    # Use BeautifulSoup to parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')
    # Extract the title of the web page
    title = soup.title.text.strip()
    return title

def extract_data(html_content):
    """Extracts relevant data from a web page given its HTML content.
    Args:
        html_content (str): The HTML content of the web page."""
    data = {}
    # Use BeautifulSoup to parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')
    # Extract the title of the web page
    data['titre'] = soup.title.text.strip()
    data['texte'] = soup.body.get_text(separator='\n', strip=True)
    return data

def extract_links(body):
    """Extracts links from the body of an email using regex.
    Args:
        body (str): The body of the email."""
    return re.findall(r'(https?://\S+)', body)

def is_alert_link(link):
    """Check if the link is a google alert link.
    Args:
        link (str): The link to check."""
    return re.search(r'/alert', link)

def timer(timeout):
    """Timer to limit the time of execution of a function.
    Args:
        timeout (int): The maximum time of execution in seconds."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            res = None
            def run():
                nonlocal res
                res = func(*args, **kwargs)
            thread = threading.Thread(target=run)
            thread.start()
            thread.join(timeout)
            return res
        return wrapper
    return decorator

def url_checker(url):
    """Check if the URL is reachable.
    Args:
        url (str): The URL to check."""
    try:
        # make it look as we are user
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        # Get Url
        get = requests.get(url, headers=headers)
        # if the request succeeds 
        if get.status_code == 200:
            return True, 200
        else:
            return False, get.status_code

    # Exception
    except requests.exceptions.RequestException as e:
        # print URL with Errs
        print(f"{url}: is Not reachable \nErr: {e}")
        return False, e
    
def get_last_date(mail_path):
    """Get the date of the last email in the database for the given mail address.
    Args:
        mail_path (str): The path to the data associated to the email."""
    if not os.path.exists(dataset_path / mail_path / info_csv_path):
        return None
    df = pd.read_csv(dataset_path / mail_path / info_csv_path)
    date = df["date"].iloc[-1]
    return date

