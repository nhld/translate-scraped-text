import requests
import re
import urllib.request
from bs4 import BeautifulSoup
from collections import deque
from html.parser import HTMLParser
from urllib.parse import urlparse
import os
import openai
from fpdf import FPDF

openai.api_key = ""

HTTP_URL_PATTERN = r'^http[s]{0,1}://.+$'

domain = "edition.cnn.com"
full_url = "https://edition.cnn.com/"

print('===== scraping on ' + domain + " =======")
TOTAL_PAGE_TO_SCRAPE = int(input("number of pages to scrape: "))

class HyperlinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hyperlinks = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "a" and "href" in attrs:
            self.hyperlinks.append(attrs["href"])


def get_hyperlinks(url):
    try:
        with urllib.request.urlopen(url) as response:
            if not response.info().get('Content-Type').startswith("text/html"):
                return []
            
            html = response.read().decode('utf-8')
    except Exception as e:
        print(e)
        return []

    parser = HyperlinkParser()
    parser.feed(html)

    return parser.hyperlinks


def get_domain_hyperlinks(local_domain, url):
    clean_links = []
    for link in set(get_hyperlinks(url)):
        clean_link = None

        if re.search(HTTP_URL_PATTERN, link):
            url_obj = urlparse(link)
            if url_obj.netloc == local_domain:
                clean_link = link
        else:
            if link.startswith("/"):
                link = link[1:]
            elif (
                link.startswith("#")
                or link.startswith("mailto:")
                or link.startswith("tel:")
            ):
                continue
            clean_link = "https://" + local_domain + "/" + link
        if clean_link is not None:
            if clean_link.endswith("html"):
                if clean_link.endswith("/") :
                    clean_link = clean_link[:-1]
                clean_links.append(clean_link)
        
        #print('.')
    return list(set(clean_links))


def crawl(url):
    local_domain = urlparse(url).netloc
    queue = deque([url])
    
    seen = set([url])

    if not os.path.exists("text/"):
            os.mkdir("text/")

    if not os.path.exists("text/"+local_domain+"/"):
            os.mkdir("text/" + local_domain + "/")

    counter = 0
    while queue:
        if (counter == TOTAL_PAGE_TO_SCRAPE + 1):
            print("scraped pages: " + str(counter-1) + " (ignore the first one)")
            break
        print(counter)
        counter += 1
        
        url = queue.pop()
        print(url) 

        with open('text/'+local_domain+'/'+url[8:].replace("/", "_") + ".txt", "w", encoding="UTF-8") as f:
            soup = BeautifulSoup(requests.get(url).text, "html.parser")
            text = soup.findAll('p')
            
            
            if ("You need to enable JavaScript to run this app." in text):
                print("Unable to parse page " + url + " due to JavaScript being required")
            
            for txt in text:
                text_p_tag = txt.get_text()
                f.write(text_p_tag)
            

        for link in get_domain_hyperlinks(local_domain, url):
            if link not in seen:
                queue.append(link)
                seen.add(link)

crawl(full_url)

LANGUAGE = input("translate to: ")


def string_to_pdf(text, output_file):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', size=12)
    encoded_text = text.encode('latin-1', errors='ignore')
    pdf.multi_cell(0, 10, encoded_text.decode('latin-1'))
    pdf.output(output_file)


for file in os.listdir("text/" + domain + "/"):
    with open("text/" + domain + "/" + file, "r", encoding="UTF-8") as f:
        text = f.read()
        #print(text)
        
        promt_ = "translate the following to " + LANGUAGE + ": " + text
        
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=promt_,
            temperature=0.3,
            max_tokens=1000,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        #res_text = response['choices'][0]['text']
        #print(res_text)
        #print(response)
        
        print("translating...")
        if not os.path.exists("pdf"):
            os.mkdir("pdf")

        filepath = "pdf/"
        filename = filepath + file + ".pdf"

        #res_text = response['choices'][0]['text']
        string_to_pdf(str(response['choices'][0]['text']), filename)
        print("saved to pdf")
       