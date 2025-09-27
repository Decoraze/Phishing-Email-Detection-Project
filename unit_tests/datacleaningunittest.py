from datacleaning import datacleaning
import unittest

clean = datacleaning()

#clean.cleanfile("testingdata.txt")
#cleaned_text, emails, domains, urls, ips = clean.cleantext("hi http://scam.com")
#print(cleaned_text)
# print(emails)
# print(ips)
#print(urls)


class TestDataCleaning(unittest.TestCase):
    def test_cleantext_with_ip_and_port(self):
        #test strings with valid ips and ports
        input_text = "input text here 192.168.12.1:8080 or 192.168.12.2."
        cleaned_text, emails, domains, urls, ips = clean.cleantext(input_text)
        expected_cleaned_text = "input text"
        expected_emails = []
        expected_domains = []
        expected_urls = []
        expected_ips = ["192.168.12.1:8080","192.168.12.2"]

        self.assertEqual(cleaned_text, expected_cleaned_text)
        self.assertCountEqual(emails, expected_emails)
        self.assertCountEqual(domains, expected_domains)
        self.assertCountEqual(urls, expected_urls)
        self.assertCountEqual(ips, expected_ips)

    def test_cleantext_with_email(self):
        #test strings with valid emails
        input_text = "my email is 1002@outlook.com or also zhang@gmail.com"
        cleaned_text, emails, domains, urls, ips = clean.cleantext(input_text)
        expected_cleaned_text = "email also"
        expected_emails = ["1002@outlook.com","zhang@gmail.com"]
        expected_domains = ["outlook.com","gmail.com"]
        expected_urls = []
        expected_ips = []
        self.assertEqual(cleaned_text, expected_cleaned_text)
        self.assertCountEqual(emails, expected_emails)
        self.assertCountEqual(domains, expected_domains)
        self.assertCountEqual(urls, expected_urls)
        self.assertCountEqual(ips, expected_ips)

    def test_cleantext_with_urls(self):
        #test strings with valid URLS
        input_text = "my website is https://www.notscam.com and www.wow.co.uk"
        cleaned_text, emails, domains, urls, ips = clean.cleantext(input_text)
        expected_cleaned_text = "websit"
        expected_emails = []
        expected_domains = []
        expected_urls = ["https://www.notscam.com","www.wow.co.uk"]
        expected_ips = []

        self.assertEqual(cleaned_text, expected_cleaned_text)
        self.assertCountEqual(emails, expected_emails)
        self.assertCountEqual(domains, expected_domains)
        self.assertCountEqual(urls, expected_urls)
        self.assertCountEqual(ips, expected_ips)

    def test_cleantext_invalid_formats(self):
        # Test strings that are not valid emails, URLs, or IPs
        input_text = "test@.com this is not an email. Also 999.999.999.999. A fake URL: htts://fake.com"
        cleaned_text, emails, domains, urls, ips = clean.cleantext(input_text)
        
        # Expected output should not contain any of the invalid formats
        expected_cleaned_text = "testcom email also 999999999999 a fake url httsfakecom"
        expected_emails = []
        expected_domains = []
        expected_urls = []
        expected_ips = []

        self.assertEqual(cleaned_text, expected_cleaned_text)
        self.assertCountEqual(emails, expected_emails)
        self.assertCountEqual(domains, expected_domains)
        self.assertCountEqual(urls, expected_urls)
        self.assertCountEqual(ips, expected_ips)

    def test_cleantext_empty_input(self):
        #test empty input
        input_text = ""
        cleaned_text, emails, domains, urls, ips = clean.cleantext(input_text)
        
        expected_cleaned_text = ""
        expected_emails = []
        expected_domains = []
        expected_urls = []
        expected_ips = []
        
        self.assertEqual(cleaned_text, expected_cleaned_text)
        self.assertCountEqual(emails, expected_emails)
        self.assertCountEqual(domains, expected_domains)
        self.assertCountEqual(urls, expected_urls)
        self.assertCountEqual(ips, expected_ips)

    def test_cleanfile_invalidfile(self):
        #cleanfile function ensures that the file provided exists
        output = clean.cleanfile("testingdatas.txt")
        self.assertEqual(output,"File does not exist")
if __name__ == '__main__':
    unittest.main()