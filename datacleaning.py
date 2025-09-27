import re #regular expressions
import nltk #pip install nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

import csv
import os


stemmer = PorterStemmer()


class datacleaning:
    #ensure there are characters before and after @. 
    email_pattern = r'[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}'
    #matches http and https 
    url_pattern = r'(https?://[^\s?]+|www\.[^\s?]+)'
    #ensure ip address values are valid which is less than 255
    ip_pattern = ipv4_pattern_with_params = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:[^\s.]*)'
    nltk.download('stopwords')
    stop_words = set(stopwords.words('english'))
    def __init__(self):
        # Initialize resources once when the class is created
        self.stemmer = PorterStemmer()
    def cleantext(self,body):
        #Extracting and storing email, domain and url data
        emails = re.findall(self.email_pattern, body)
        #set make sure that my list values are unique
        emails = list(set([email.removesuffix('.') for email in emails]))
        urls = re.findall(self.url_pattern,body)
        urls = list(set([url.removesuffix('.') for url in urls]))
        ips = re.findall(self.ip_pattern, body)
        ips = list(set(ips))
        domains = [email.split('@')[-1] for email in emails]
        

        # Remove emails and urls from data
        cleaned_text = body
        cleaned_text = re.sub(self.email_pattern, '', cleaned_text)
        cleaned_text = re.sub(self.url_pattern, '', cleaned_text)
        cleaned_text = re.sub(self.ip_pattern, '', cleaned_text)
        #removed punctuations
        cleaned_text = re.sub(r'[^\w\s]', '', cleaned_text) 

        #remove stop words
        words = cleaned_text.split()
        words = [w for w in words if w not in self.stop_words]
        

        #stemming words into base words,
        words = [stemmer.stem(w) for w in words]
        cleaned_text = " ".join(words)

        return cleaned_text, emails, domains, urls, ips


    def cleanfile(self,file):
        rows = []

        file_name = file.replace(".txt", "")
        output_dir = "cleaned_data"
        try:
            with open("test data/"+file, "r", encoding="utf-8") as f:
                
                for line in f:
                    line = line.strip()
                    #if line is empty, skip line
                    if not line:
                        continue
                    # split only at the first tab (or whitespace if that's the case)
                    parts = line.split("\t", 1)  
                    if len(parts) == 2:
                        label, body = parts
                        if label == "No":
                            label = 1
                        elif label == "Yes":
                            label = 0
                        else:
                            #if label is not "yes" or "no" skips line
                            continue
                        


                        cleaned_text, emails, domains, urls, ips = self.cleantext(body)
                        emails = "\n".join(emails)
                        domains = "\n".join(domains)
                        urls = "\n".join(urls)
                        ips = "\n".join(ips)

                        rows.append({"label": label, "body": cleaned_text, "emails": emails, "domains": domains, "urls": urls, "ips": ips})

        except:
            output = "File does not exist"
            print(output)
            return output
                    


        # Save as CSV
        output_path = output_dir + "/cleaned_" + file_name + ".csv"
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["label", "body","emails","domains","urls","ips"])
            writer.writeheader()
            writer.writerows(rows)

        print("Saved", len(rows), "rows to " + file_name + ".csv")
        
        

        
        
        


