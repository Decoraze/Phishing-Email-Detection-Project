import unittest

from ruleset import (                        #RULESET.PY TEST
    safe_domain_check,
    suspicious_keyword_check,
    keyword_position_scoring,
    levenshtein_distance,
    lookalike_domain_check,
    suspicious_url_detection,
    ruleset
)

class TestRuleSet(unittest.TestCase):

    def test_safe_domain_check(self):
        self.assertEqual(safe_domain_check("user@gov.sg"), 0)     # safe domain
        self.assertEqual(safe_domain_check("user@scam.com"), 2) # unsafe domain

    def test_suspicious_keyword_check(self):
        subject = "Urgent account verification"
        body = "Please verify your password immediately"
        self.assertGreater(suspicious_keyword_check(subject, body), 0)

    def test_keyword_position_scoring(self):
        subject = "Verify your account"
        body = "This content is safe"
        score = keyword_position_scoring(subject, body)
        self.assertGreaterEqual(score, 2)   # subject keyword = +2

    def test_levenshtein_distance(self):
        self.assertEqual(levenshtein_distance("abc", "abc"), 0)
        self.assertEqual(levenshtein_distance("abc", "abd"), 1)

    def test_lookalike_domain_check(self):
        self.assertEqual(lookalike_domain_check("gov.sg"), 0)  # exact safe domain
        self.assertEqual(lookalike_domain_check("g0v.sg"), 3)  # typo fake domain


    def test_suspicious_url_detection(self):
        body = "Click http://192.168.0.1 or http://scam.com"
        score, urls = suspicious_url_detection(body)
        self.assertEqual(score, 4)   # 2 urls 2 points each
        self.assertIn("http://scam.com", urls)
        
#calculator and processor unit test to be added







if __name__ == "__main__":
    unittest.main()

