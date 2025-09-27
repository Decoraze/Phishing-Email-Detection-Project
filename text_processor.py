import re
import regex #faster processing for regex operations
from typing import Dict, Optional, Set #mainly for inline documentation to show what functions and output types are expected
from functools import lru_cache 
'''
helps with time complexity O(1) for repeated calls with same input. Built in LRU (least recently used) eviction (cachemanagement strategy to 
manage when the cache is full and  anew item is required to be added. The one accessed the longest time ago will be removed to make space)

'''
import hashlib
'''
Longer text strings from the text input/email body that will be used as dictionary keys will be hashed to reduce memory usage using MD5 which
limits the text to 32 characters hexadecimal string. This when doing dictionary lookups will ensure that it is O(1) time complexity with consistent
key sizes. 

Memory usage will also be standardised and reduced. 

'''
import time #used for logging and performance measurement. Its not affected by system clock and is suitable for measuring time intervals.

class OptimizedTextProcessor:

    def __init__(self, cache_size: int = 100): #initialize instance variables the processor requires and by initialising 100 for the cache size 

        '''
        100 is specified for 100 files to be cached as it is not too big of a number. It also does not benefit being a multiple of 2 like 128. 
        '''
        self.cache_size = cache_size #size of the cache for lru_cache
        self._result_cache = {} #dictionary to store cached results for text processing 
        self._cache_timeout = 3600 #necessary to prevent stale data problems and memory leaks in long running applications. This prevents old cached results to persist. Since older results are likely not needed, and a user session is usually not too long around an hour, 3600s is perfect. 
        self._compiled_patterns = self._setup_patterns() #precompile regex patterns for efficiency

        '''
        Performance monitoring is important to count successful calls, track when cache results are returned (higher hits the better performance)
        Tracks when processing is required and not cached. Also tracks total processing time to identify bottlenecks and areas for improvement.

        '''

        self.stats = {
            'total_processed': 0, #consistent naming with rest of application
            'cache_hits': 0,
            'cache_misses': 0,
            'total_processing_time': 0
        }
    
    def _setup_patterns(self) -> Dict[str, any]:
        '''
        Precompile regex patterns for efficiency. This reduces the overhead of compiling patterns on each call. e.g. iterating in for
        loops to find matches. (this is not optimal for O(n) time complexity)
        '''
        patterns = { #nested lists in dictionaries ensure O(1) time complexity for lookups
            'subject_patterns': 
            [
                #Subject: \s*: space,tabs (xxx): capture group .+?: any character but newlines, one or more occurences, stops at first match. 
                #(?: ...) doesn't create match group  \n: finds a new line (end of the subject line), $: end of string if its the last line. 
                # IGNORECASE: case insensitive ignore. MULTILINE: matches the end of each line instead of the end of the entire string 

                regex.compile(r'Subject:\s*(.+?)(?:\n|$)', regex.IGNORECASE | regex.MULTILINE),
                regex.compile(r'RE:\s*(.+?)(?:\n|$)', regex.IGNORECASE | regex.MULTILINE),
                regex.compile(r'FW:\s*(.+?)(?:\n|$)', regex.IGNORECASE | regex.MULTILINE),
                regex.compile(r'Fwd:\s*(.+?)(?:\n|$)', regex.IGNORECASE | regex.MULTILINE)
            ],
            
            'sender_patterns': 
            [
                regex.compile(r'From:\s*(.+?)(?:\n|$)', regex.IGNORECASE | regex.MULTILINE),
                regex.compile(r'Sender:\s*(.+?)(?:\n|$)', regex.IGNORECASE | regex.MULTILINE)
            ],
            
            # Add missing recipient patterns
            'recipient_patterns': [
                regex.compile(r'To:\s*(.+?)(?:\n|$)', regex.IGNORECASE | regex.MULTILINE),
                regex.compile(r'Cc:\s*(.+?)(?:\n|$)', regex.IGNORECASE | regex.MULTILINE),
                regex.compile(r'Bcc:\s*(.+?)(?:\n|$)', regex.IGNORECASE | regex.MULTILINE)
            ],
            
            # Add missing forensic patterns
            'forensic_patterns': [
                regex.compile(r'Message-ID:\s*(.+?)(?:\n|$)', regex.IGNORECASE | regex.MULTILINE),
                regex.compile(r'Date:\s*(.+?)(?:\n|$)', regex.IGNORECASE | regex.MULTILINE),
                regex.compile(r'Reply-To:\s*(.+?)(?:\n|$)', regex.IGNORECASE | regex.MULTILINE)
            ],

            'email_pattern': regex.compile(
            r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}',#standard email format regex 
            regex.IGNORECASE
            ),
            
            # Remove only noise headers (preserve forensically important ones)
            'noise_header_removal': [
                regex.compile(pattern, regex.IGNORECASE | regex.MULTILINE)
                for pattern in [
                    r'Received:\s*.*?(?:\n|$)',                    # Email routing info
                    r'Return-Path:\s*.*?(?:\n|$)',                # Return routing  
                    r'X-[A-Za-z0-9-]+:\s*.*?(?:\n|$)',           # Technical headers
                    r'Content-Type:\s*.*?(?:\n|$)',              # File type info
                    r'Content-Transfer-Encoding:\s*.*?(?:\n|$)', # Encoding info
                    r'MIME-Version:\s*.*?(?:\n|$)',              # Email format version
                    r'User-Agent:\s*.*?(?:\n|$)',                # Email program used
                ]
            ],
            # Text cleanup patterns
            'cleanup': {
                'mime_encoding': regex.compile(r'=\?.*?\?='),
                'line_endings': regex.compile(r'\r\n|\r|\n'),
                'whitespace': regex.compile(r'\s+'),
                'non_printable': regex.compile(r'[^\x20-\x7E]'),
                'prefixes': regex.compile(r'^\s*(?:RE|FW|FWD|Fwd|Re|Fw):\s*', regex.IGNORECASE),
            }
        }
        return patterns
    
    def process_text(self, text_content: str, debug: bool = False) -> str:
        '''
        self is used as this is still instanced in a class. text content is then specified to be a string and a debug variable is also set incase
        debugging is required. -> str specifies that this function returns a string. 
        '''

        start_time = time.perf_counter() #measure accurate time for execution by storing the starting time for later 

        cache_key = self._generate_cache_key(text_content) #generate a unique cache key for the input text content
        cached_result = self._get_cached_result(cache_key) #check to see if the result has been cached 

        if cached_result: #if the result is cached
            self.stats['cache_hits'] += 1 #initialise cache hits and increment it by 1 to track performance
            if debug: #if debugging is = true, print out cache hit for the key and the respecitve cache key 
                print(f"Cache hit for key: {cache_key[:16]}...")
            return cached_result 
        
        self.stats['cache_misses'] += 1 #increment cache misses if result is not cached. no else to reduce nested blocks easier to read

        try:
            email_data = self._parse_email_text_with_headers(text_content) #header content parsed through function
            result = self._format_phishing_aware_output(email_data, debug)#clean the output for analysis 
            self._cache_result(cache_key, result) #cache the result for future use (still deleting after 1h)

            processing_time = time.perf_counter() - start_time #accurate processing time after subtraction of start time
            self.stats['total_processing_time'] += processing_time #increment total processing time by the previous result to monitor performance
            self.stats['total_processed'] += 1 #increment total processed by 1 to monitor performance

            #print debug information if required. 
            if debug:
                print(f"Processed {len(text_content)} chars in {processing_time:.4f}s")
                print(f"Found email parts: {list(email_data.keys())}")
        
            return result
        
        except Exception as e:
            if debug:
                print(f"ERROR IN PROCESSING: {e}")
            return "" #return empty string if error occurs to ensure smooth execution
        
    def _generate_cache_key(self, text_content: str) -> str:
        #generate unique cache key using MD5 (efficient)

        
        if len(text_content) > 1000: #1000 and not lower is due to lower collision risks when handling the unique hashes 
            text_sample = text_content[:1000]#only use the first 1000 characters to limit the size of the key
        else:
            text_sample = text_content

        hash_result = hashlib.md5(text_sample.encode('utf-8', errors='ignore')).hexdigest() #hash the text sample using MD5 and encode it to utf-8 (standard practice)
        return hash_result
    
    def _get_cached_result(self, cache_key: str) -> Optional[str]:
        """Retrieve cached result if valid."""
        if cache_key in self._result_cache:
            result, timestamp = self._result_cache[cache_key] #unpack the tuple stored in the cache
            if time.time() - timestamp < self._cache_timeout: #how much time passed since caching < 3600s return the result 
                return result
            else:
                del self._result_cache[cache_key] #if too much time has passed, delete cache 
        return None
    
    def _cache_result(self, cache_key: str, result: str):
        """Cache result with size management."""
        if len(self._result_cache) >= self.cache_size: #if the cache (.result_cache) is greater than cache size (100)
            # Remove oldest 20% of entries to manage cache size
            sorted_items = sorted(self._result_cache.items(), key=lambda x: x[1][1])
            remove_count = len(sorted_items) // 5 #1/5th of the cache size 
            for i in range(remove_count): #remove the oldest items in the cache using for loop
                del self._result_cache[sorted_items[i][0]] #delete item
        
        self._result_cache[cache_key] = (result, time.time())#store cache key with result and timestampped it to track for debugging and timeout purposes

    def _parse_email_text_with_headers(self, text: str) -> Dict[str, str]:
        """Parse email text preserving forensically important headers."""
        email_data = {#create dictionary to store extracted values with empty keys as defaults
            'subject': '', 'from': '', 'to': '', 'cc': '', 'bcc': '',
            'message_id': '', 'date': '', 'reply_to': '', 'body': text
        }
        
        # Extract subject (remove from body after extraction) this is to ensure that there isnt a duplication of subject in the body 
        for pattern in self._compiled_patterns['subject_patterns']:
            match = pattern.search(text)#using regex library to search for patterns in the given text 
            if match:
                email_data['subject'] = match.group(1).strip() #if true populate the dictionary with subject value and captures it in group 1 for the capture group specified above
                email_data['body'] = pattern.sub('', email_data['body'], count=1) #with .sub from regex, it replaces the matched pattern with an empty string in the (emaildata body) and only the first occurance is replaced
                break
        
        # Extract sender information same as above, remove data from the body after extraction to prevent dupes 
        for pattern in self._compiled_patterns['sender_patterns']:
            match = pattern.search(text)#using regex library to search for patterns in the given text 
            if match:
                email_data['from'] = match.group(1).strip() #if found, populate the dictionary with sender value and capture it in group 1 and strip spaces
                email_data['body'] = pattern.sub('', email_data['body'], count=1)#replace matched patter with .sub, finding the matching string in the body and replaces it with an empty string and only the first occurance is replaced
                break
        
        # Extract recipient information
        recipient_fields = ['to', 'cc', 'bcc'] #3 types of recipient fields 
        for i, field_name in enumerate(recipient_fields): #due to the nested list structure, i is the index and field name is the string field name value. We use enumerate here to ensure that we can associate the field name with the position id 
            if i < len(self._compiled_patterns['recipient_patterns']): #this is to prevent index error as it checks for the number of patterns there are and avoids any excess i values
                pattern = self._compiled_patterns['recipient_patterns'][i] #[atter is equals to in compiled pattern, the enumerated index value e.g. i = 1 is CC, 0 is TO and 2 is BCC. 
                match = pattern.search(text) #finds whether the recipient pattern above matches anything in the text 
                if match:
                    email_data[field_name] = match.group(1).strip()#if match, find the group 1 value that is captured and strip the spaces 
                    email_data['body'] = pattern.sub('', email_data['body'], count=1) #replace matched pattern with empty string and only the first occurance in the body. 
        
        # Extract forensic headers
        forensic_fields = ['message_id', 'date', 'reply_to'] #similar to recipient fields but for forensic headers 
        for i, field_name in enumerate(forensic_fields):
            if i < len(self._compiled_patterns['forensic_patterns']):
                pattern = self._compiled_patterns['forensic_patterns'][i]
                match = pattern.search(text)
                if match:
                    email_data[field_name] = match.group(1).strip()
                    email_data['body'] = pattern.sub('', email_data['body'], count=1)
        
        # Fallback email detection
        if not email_data['from']:#if no from: information is found
            email_match = self._compiled_patterns['email_pattern'].search(text)#search for an email pattern in text
            if email_match: #if a match is found
                email_data['from'] = email_match.group(0)#assign from data to the found email address. This is to ensure that there is an address for an email to be sent from (no such thing as an email without a sender) this is a fall back 
        
        return email_data #returns the poplulated dictionary 
    
    def _format_phishing_aware_output(self, email_data: Dict[str, str], debug: bool = False) -> str:
        """Format output preserving phishing detection features."""
        subject = self._clean_subject(email_data.get('subject', '')) #call cleaning function to clean subject line from noise e.g. MIME encoding
        sender = self._clean_sender(email_data.get('from', '')) #call sender function to clean sender line from noise e.g. 
        recipients = self._clean_recipients(email_data) #call recipient function to clean recipient line from noise e.g. 
        forensic_info = self._clean_forensic_headers(email_data)# clean message id date and reply to headers from noise e.g.
        body = self._clean_body_preserve_structure(email_data.get('body', ''))# clean body lol
        
        if debug:
            print(f"Components - Subject: {len(subject)}, Sender: {len(sender)}, Body: {len(body)} chars")
        
        # Build structured output
        output_parts = [] #compile the output parts into a list for managing and formatting
        if subject:
            output_parts.append(f"Subject: {subject}") #append data cleaned to subject 
        if sender:
            output_parts.append(f"From: {sender}") #append data cleaned to sender
        if recipients:
            output_parts.append(f"Recipients: {recipients}")# append data cleaned to recipients
        if forensic_info:
            output_parts.append(f"Forensic: {forensic_info}")# append data cleaned to forensic info
        
        if body:
            output_parts.append("---")# append separator as indication of body start
            output_parts.append(body)# append body cleaned 
        
        result = '\n'.join(output_parts)# join output parts with new lines to read
        return self._compiled_patterns['cleanup']['whitespace'].sub(' ', result).strip() #clean up any whitespaces and replace them with empty strings 
    
    def _clean_subject(self, subject: str) -> str:
        """Clean subject line preserving phishing indicators."""
        if not subject:
            return ""
        
        cleanup = self._compiled_patterns['cleanup']
        subject = cleanup['mime_encoding'].sub('', subject)
        subject = cleanup['non_printable'].sub(' ', subject)
        subject = cleanup['whitespace'].sub(' ', subject).strip()
        return subject
    
    def _clean_sender(self, sender: str) -> str:
        """Clean sender preserving spoofing indicators."""
        if not sender:
            return ""
        
        # Handle "Name <email@domain.com>" format
        angle_bracket_match = regex.match(r'^(.*?)\s*<([^>]+)>\s*$', sender)
        if angle_bracket_match:
            name = angle_bracket_match.group(1).strip()
            email = angle_bracket_match.group(2).strip()
            
            name = regex.sub(r'^["\'](.*)["\']$', r'\1', name)
            name = self._compiled_patterns['cleanup']['non_printable'].sub(' ', name)
            name = self._compiled_patterns['cleanup']['whitespace'].sub(' ', name).strip()
            
            if name and email:
                return f"{name} <{email}>"
            return email or name
        
        cleanup = self._compiled_patterns['cleanup']
        sender = regex.sub(r'^["\'](.*)["\']$', r'\1', sender)
        sender = cleanup['non_printable'].sub(' ', sender)
        sender = cleanup['whitespace'].sub(' ', sender).strip()
        return sender
    
    def _clean_recipients(self, email_data: Dict[str, str]) -> str:
        """Combine and clean recipient information."""
        recipients = []
        for field in ['to', 'cc', 'bcc']:
            value = email_data.get(field, '').strip()
            if value:
                cleaned = self._clean_sender(value)
                if cleaned:
                    recipients.append(f"{field.upper()}:{cleaned}")
        return " | ".join(recipients)
    
    def _clean_forensic_headers(self, email_data: Dict[str, str]) -> str:
        """Clean and preserve forensic headers."""
        forensic_parts = []
        
        msg_id = email_data.get('message_id', '').strip()
        if msg_id:
            msg_id = self._compiled_patterns['cleanup']['non_printable'].sub('', msg_id)
            forensic_parts.append(f"ID:{msg_id}")
        
        date = email_data.get('date', '').strip()
        if date:
            date = self._compiled_patterns['cleanup']['non_printable'].sub(' ', date)
            date = self._compiled_patterns['cleanup']['whitespace'].sub(' ', date).strip()
            forensic_parts.append(f"Date:{date}")
        
        reply_to = email_data.get('reply_to', '').strip()
        if reply_to:
            reply_to = self._clean_sender(reply_to)
            forensic_parts.append(f"ReplyTo:{reply_to}")
        
        return " | ".join(forensic_parts)
    
    def _clean_body_preserve_structure(self, body: str) -> str:
        """Clean body while preserving structure for phishing analysis."""
        if not body:
            return ""
        
        # Remove only noise headers
        for pattern in self._compiled_patterns['noise_header_removal']:
            body = pattern.sub('', body)
        
        cleanup = self._compiled_patterns['cleanup']
        body = cleanup['line_endings'].sub(' ', body)
        body = regex.sub(r'^>\s*', '', body, flags=regex.MULTILINE)
        
        # Keep URLs for phishing analysis
        body = cleanup['non_printable'].sub(' ', body)
        body = cleanup['whitespace'].sub(' ', body)
        
        return body.strip()
    
    def get_performance_stats(self) -> Dict[str, any]:
        """Get performance statistics."""
        total_requests = self.stats['cache_hits'] + self.stats['cache_misses']
        
        return {
            'total_processed': self.stats['total_processed'],
            'cache_hits': self.stats['cache_hits'],
            'cache_misses': self.stats['cache_misses'],
            'cache_hit_rate': (
                self.stats['cache_hits'] / total_requests 
                if total_requests > 0 else 0
            ),
            'average_processing_time': (
                self.stats['total_processing_time'] / self.stats['total_processed']
                if self.stats['total_processed'] > 0 else 0
            ),
            'cache_size': len(self._result_cache)
        }

# Global processor instance
_processor_instance = None

def get_processor():
    """Get the email processor instance (singleton pattern)."""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = OptimizedTextProcessor(cache_size=100)
    return _processor_instance

def process_email_text(text_content: str, debug: bool = False) -> str:
    """Simple function to process email text."""
    processor = get_processor()
    return processor.process_text(text_content, debug)