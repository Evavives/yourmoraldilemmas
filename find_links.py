# Search for new emails and update the database

from pathlib import Path
import pandas as pd
import os
import imaplib
import email
from email.utils import parsedate_tz, mktime_tz, formatdate
import re
import dotenv
from utils import extract_data_trafi, extract_links, timer, url_checker, get_last_date, get_alert_links, dataset_path, csv_file_path, info_csv_path, txt_files_path, data_path, sender


def main():
    dotenv.load_dotenv()
    EMAIL = os.getenv("EMAIL")
    PASSWORD = os.getenv("PASSWORD")
    EMAIL_EVA = os.getenv("EMAIL_EVA")
    PASSWORD_EVA = os.getenv("PASSWORD_EVA")
    PASSWORDS = [PASSWORD, PASSWORD_EVA]
    EMAILS = [EMAIL, EMAIL_EVA]
    SERVER = os.getenv("SERVER")
    for EMAIL, PASSWORD in zip(EMAILS, PASSWORDS):
        # Connection to the mailbox
        mail = imaplib.IMAP4_SSL(SERVER)
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")  # Sélection de la boîte de réception

        print("Connected to the mailbox for", EMAIL)
        # Parameters
        save_text_in_file = False
        mail_path = Path(EMAIL.split('@')[0])
        
        
        if not os.path.exists(dataset_path):
            os.mkdir(dataset_path)
        if not os.path.exists(dataset_path / mail_path):
            os.mkdir(dataset_path / mail_path)
        if not os.path.exists(dataset_path / mail_path / data_path):
            os.mkdir(dataset_path / mail_path / data_path)
        
        if save_text_in_file:
            if not os.path.exists(dataset_path / txt_files_path):
                os.mkdir(dataset_path / txt_files_path)
        
        status, data = mail.search(None, 'FROM', sender)
        date_list = []
        links_list = []
        last_dates = []
        csv_paths = []
        nb_csv = 0
        nb_url = 0
        count = 0
        for num in data[0].split()[count:]:
            try:
                status, data = mail.fetch(num, '(RFC822)')
            except Exception as e:
                print(e)
                continue

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            links = []
            # extract links from the email body
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    try:
                        body = part.get_payload(decode=True).decode()
                    except:
                        continue
                    if "attachment" not in content_disposition:
                        link = extract_links(body)
                        for l in link:
                            # extract link inside the link between &url= and &ct=
                            alert_link = re.findall(r'&url=(.*)&ct=', l)
                            links.extend(alert_link)
            else:
                body = msg.get_payload(decode=True).decode()
                links = extract_links(body)
                for l in link:
                    # extract link inside the link between &url= and &ct=
                    alert_link = re.findall(r'&url=(.*)&ct=', l)
                    if alert_link:
                        print("found alert link")
                    links.extend(alert_link)                    
            
            # extract date from the email
            date = msg.get("Date")
            if date is not None:
                date = parsedate_tz(date)
                date = formatdate(mktime_tz(date))
                for i in range(len(links)):
                    date_list.append(date)
            else:
                print('No date found in the email')
                for i in range(len(links)):
                    date_list.append(None)
            links_list.extend(links)
            count += 1

                    
            if count%20 == 0:
                print(f"{count} emails parsed...")
            if count%100 == 0:
                # Creation of a dataframe
                reachable = []
                code_error = []
                texts = []

                for l in links_list:
                    # Check if the URL is reachable
                    check = timer(500)(url_checker)(l)
                    if check is None:
                        print("Artificial timeout")
                        check = (False, 408)
                    reachable.append(check[0])
                    code_error.append(check[1])
                    if check[0]:
                        # Extract the data from the URL
                        text, title = extract_data_trafi(l)
                        if text is None:
                            text = ""
                        if save_text_in_file:
                            filename = title.replace(':','') + ".txt"
                            with open(dataset_path / txt_files_path  / Path(filename), 'w', encoding='utf-8') as f:
                                f.write(text)
                            texts.append(filename)
                        else:
                            texts.append(text)
                    else:
                        texts.append(None)
                    nb_url += 1
                    if nb_url%20 == 0:
                        print(f"{nb_url} urls explored...")
                
                print("Done")
                print("Creating CSV file...")



                df = pd.DataFrame(links_list, columns=['Links'])
                df['Reachable'] = reachable
                df['Code'] = code_error
                df['Text'] = texts
                df['Date'] = date_list
                # Save the data in a CSV file
                df.to_csv(dataset_path / mail_path / data_path / Path(csv_file_path + '_' + str(nb_csv) + ".csv"), index=False)
                print(f"CSV {nb_csv} file created")
                nb_csv += 1
                last_dates.append(date_list[-1])
                csv_paths.append(str(csv_file_path) + '_' + str(nb_csv) + ".csv")
                date_list = []
                links_list = []
                

        # Creation of a dataframe
        reachable = []
        code_error = []
        texts = []
        print("checking urls...")
        for l in links_list:
            # Check if the URL is reachable
            check = url_checker(l)
            reachable.append(check[0])
            code_error.append(check[1])
            if check[0]:
                # Extract the data from the URL
                text, title = extract_data_trafi(l)
                if text is None:
                    text = ""
                if save_text_in_file:
                    filename = title.replace(':','') + ".txt"
                    with open(dataset_path / txt_files_path / Path(filename), 'w', encoding='utf-8') as f:
                        f.write(text)
                    texts.append(filename)
                else:
                    texts.append(text)
            else:
                texts.append(None)
            nb_url += 1
            if nb_url%20 == 0:
                print(f"{nb_url} urls explored...")
        
        print("Done")
        print("Creating CSV file...")


        df = pd.DataFrame(links_list, columns=['Links'])
        df['Reachable'] = reachable
        df['Code'] = code_error
        df['Text'] = texts
        df['Date'] = date_list
        # Save the data in a CSV file
        df.to_csv(dataset_path / mail_path / data_path / Path(csv_file_path + '_' + str(nb_csv) + ".csv"), index=False)
        print(f"CSV {nb_csv} file created")
        if date_list:
            last_dates.append(date_list[-1])
        else:
            last_dates.append(None)
        csv_paths.append(str(csv_file_path) + '_' + str(nb_csv) + ".csv")
        if not os.path.exists(dataset_path / info_csv_path):
            df_info = pd.DataFrame(last_dates, columns=['date'])
            df_info['path'] = csv_paths
            df_info.to_csv(dataset_path / mail_path / info_csv_path, index=False)
        else:
            df_info_original = pd.read_csv(dataset_path / mail_path/ info_csv_path)
            df_info = pd.DataFrame(last_dates, columns=['date'])
            df_info['path'] = csv_paths
            df_info = pd.concat([df_info_original, df_info])
            df_info.to_csv(dataset_path / mail_path/ info_csv_path, index=False)
        print("End")

if __name__ == "__main__":
    main()
