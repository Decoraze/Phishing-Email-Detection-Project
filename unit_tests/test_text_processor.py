import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text_processor import OptimizedTextProcessor, process_email_text

class TestEmailProcessor(unittest.TestCase):
    
    def setUp(self):
        self.processor = OptimizedTextProcessor(cache_size=5)
        self.test_email ="""
                            Subject: Test Email
                            From: sender@example.com
                            To: recipient@example.com
                            Date: Mon, 15 Jan 2024 12:00:00
                            Message-ID: <test123@example.com>
                            X-Spam: remove this header

                            This is the email body content.
                          """

    def test_email_parsing(self):
        """Test basic email component extraction."""
        result = self.processor.process_text(self.test_email)
        
        # Check essential parts are present
        self.assertIn("Subject: Test Email", result)
        self.assertIn("From: sender@example.com", result)
        self.assertIn("Recipients: TO:recipient@example.com", result)
        self.assertIn("email body content", result)
        
        # Check noise headers removed
        self.assertNotIn("X-Spam", result)

    def test_caching(self):
        """Test cache functionality."""
        # First call - cache miss
        result1 = self.processor.process_text(self.test_email)
        self.assertEqual(self.processor.stats['cache_misses'], 1)
        
        # Second call - cache hit
        result2 = self.processor.process_text(self.test_email)
        self.assertEqual(self.processor.stats['cache_hits'], 1)
        self.assertEqual(result1, result2)

    def test_malformed_input(self):
        """Test handling of malformed emails."""
        test_cases = ["", "No headers", "Subject:\nFrom:\nEmpty fields"]
        
        for case in test_cases:
            result = self.processor.process_text(case)
            self.assertIsInstance(result, str)

    def test_phishing_preservation(self):
        """Test phishing indicators are preserved."""
        phishing_email = """
                            Subject: URGENT Account Alert
                            From: security@fake-bank.com
                            Reply-To: collect@different-domain.com

                            Click here immediately: http://malicious-site.com
                        """
        
        result = self.processor.process_text(phishing_email)
        
        # Critical indicators should be preserved
        self.assertIn("URGENT", result)
        self.assertIn("fake-bank.com", result)
        self.assertIn("different-domain.com", result)
        self.assertIn("malicious-site.com", result)

    def test_performance(self):
        """Test processing doesn't hang on large input."""
        large_email = self.test_email + ("Large content. " * 1000)
        
        import time
        start = time.time()
        result = self.processor.process_text(large_email)
        duration = time.time() - start
        
        self.assertLess(duration, 0.5)  # Should complete in <0.5s
        self.assertGreater(len(result), 0)

if __name__ == '__main__':
    unittest.main(verbosity=2)