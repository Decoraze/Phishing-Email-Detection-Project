import re
from text_processor import get_processor
from nltk.stem import PorterStemmer

stemmer = PorterStemmer()

def load_keywords(filepath="suspicious_keywords.txt"):
    with open(filepath, "r", encoding="utf-8") as f:
        words = [line.strip().lower() for line in f if line.strip()]
    return [stemmer.stem(word) for word in words]

def load_safe_domains(filepath="safe_domains.csv"):
    safe_domains = set()
    with open(filepath, "r", encoding="utf-8") as f:
        next(f)  # Skip the header row
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 3:  # Ensure we have enough columns
                domain = parts[2]  # Domain is in the 3rd column (index 2)
                safe_domains.add(domain.lower())
    return safe_domains

# Load them once at startup
SUSPICIOUS_KEYWORDS = load_keywords()       
SAFE_DOMAINS = load_safe_domains("safe_domains.csv")

def safe_domain_check(provided_email):
    domain = provided_email.split("@")[-1].lower()
    if domain in SAFE_DOMAINS:                     # return a score of either 0 or 2, with 0 being safe
        return 0    
    else: 
        return 2                                  

def suspicious_keyword_check(subject,body):        # check the subject and body of email for flagged keywords
    content = subject.lower() + " " + body.lower() # separate subject and body with a 'space'   
    count = 0                                      # count for flagged keywords
    for word in SUSPICIOUS_KEYWORDS:
        if word in content:
            count += 1

    return count

def keyword_position_scoring(subject,body):
    score = 0
    body_content = body.lower().split()           # dont need to spilt subject of email because usually it is short
    for word in SUSPICIOUS_KEYWORDS:
        if  word in body_content[:15]:            # only flag if keywords appear in the first 15 words of body
            score += 1            
        elif word in subject.lower():
            score += 2                            # flagged keywords in subject are more serious
    return score 

def levenshtein_distance(a,b):                    # genuinely just copy pasted this
    dp = [[0] * (len(b)+1) for _ in range(len(a)+1)]
    for i in range(len(a)+1):
        for j in range(len(b)+1):
            if i == 0:
                dp[i][j] = j
            elif j == 0:
                dp[i][j] = i
            elif a[i-1] == b[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    
    return dp[len(a)][len(b)]


def lookalike_domain_check(domain):             # checker using levenshtein alg
    if domain in SAFE_DOMAINS:                  # exact match = safe
        return 0
    for safe in SAFE_DOMAINS:
        distance = levenshtein_distance(domain, safe)
        if distance <= 2:   # small difference means it is suspicious
            return 3        
    return 0


def suspicious_url_detection(body):     
    ips = re.findall(r"http[s]?://\d+\.\d+\.\d+\.\d+", body)       # find ip urls
    urls = re.findall(r"http[s]?://[^\s]+", body)                  # find all urls
    suspicious_urls = ips + urls
    score = len(suspicious_urls) * 2             # 2 points per flagged instance
    
    return score, suspicious_urls


def calculator(sender: str, subject: str, body: str, urlIP: str) -> tuple:  #Main ruleset score calculator returns ruleset score, keyword_count
    sender_domain = sender.split("@")[-1]                                   #calculations done with ruleset
    domain_score = safe_domain_check(sender)
    keyword_count = suspicious_keyword_check(subject, body)
    keyword_score = min(15, keyword_count)
    position_score = min(15, keyword_position_scoring(subject, body))
    lookalike_score = lookalike_domain_check(sender_domain)
    url_score, suspicious_urls = suspicious_url_detection(urlIP)
    url_score = min(15, url_score)

    total_score = domain_score + keyword_score + position_score + lookalike_score + url_score
    max_score = 50                                                                               #Max score set to 50 for now          
    ruleset_score = round((total_score / max_score) * 100, 2)                                    #calculates percentage upon 100%   

    return ruleset_score, keyword_count


def process_email_and_score(cleaned_text, emails, domains, urls, ips):   #Returns tuple (danger_level, percentage_score, keyword_count)
    sender = " ".join(emails + domains) if emails or domains else ""
    subject = cleaned_text
    body = cleaned_text
    # convert list of urls + ips into one string
    urlIP = " ".join((urls or []) + (ips or []))

    return calculator(sender, subject, body, urlIP)
'''
def main():
    print(process_email_and_score("Phishing Phishing Phishing Phishing Phishing Phishing Phishing Phishing ", [], [], [], []))

if __name__ == "__main__":
    main()
'''


