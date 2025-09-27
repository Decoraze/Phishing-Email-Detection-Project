from datacleaning import datacleaning
from NLP_ML import analyse
import requests
import subprocess
import ruleset
import joblib
import time

def main():
    """Main function - most processing logic runs here"""
    subprocess.Popen(['python', 'app.py'])  # Start Flask in background
    
    print("Starting ML processing loop...")
    
    # **NEW**: Continuous processing loop
    while True:
        try:
            process_latest_request()
            time.sleep(2)  # Check every 2 seconds
        except KeyboardInterrupt:
            print("Shutting down ML processor...")
            break
        except Exception as e:
            print(f"Processing error: {e}")
            time.sleep(5)  # Wait before retrying

def get_data_from_flask():
    """Get latest text input from Flask API (unchanged)"""
    try:
        response = requests.get('http://localhost:5000/api/get_latest')
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                return result['text']
        return ""
    except:
        return ""

# **NEW**: Main processing function that runs continuously
def process_latest_request():
    """Check for new processing requests and handle them"""
    cleaned_data = get_data_from_flask()
    
    if cleaned_data:
        print(f"Processing new request: {len(cleaned_data)} characters")
        
        # Run your existing ML pipeline
        result_data = process_user_input(cleaned_data)
        
        # Send results back to Flask
        if result_data:
            try:
                response = requests.post('http://localhost:5000/api/update_results', 
                                       json=result_data, timeout=10)
                if response.status_code == 200:
                    print("Results sent to Flask successfully")
                else:
                    print(f"Failed to send results: {response.status_code}")
            except Exception as e:
                print(f"Error sending results: {e}")

# **MODIFIED**: Process user input with the provided text
def process_user_input(cleaned_data=None):
    """Main processing function - runs your ML pipeline"""
    try:
        # Use provided data or get from Flask
        if not cleaned_data:
            cleaned_data = get_data_from_flask()
        
        if not cleaned_data:
            return None
        
        print("Starting ML analysis...")
        
        # Your existing processing pipeline
        clean = datacleaning()
        cleaned_text, emails, domains, urls, ips = clean.cleantext(cleaned_data)
        
        print("Data cleaning completed")
        
        # Ruleset analysis
        ruleset_score, keyword_count = ruleset.process_email_and_score(
            cleaned_text, emails, domains, urls, ips
        )
        
        print(f"Ruleset analysis completed: score={ruleset_score}, keywords={keyword_count}")
        
        # ML analysis
        loaded_model = joblib.load('model/model_trained.joblib')
        probability = analyse(loaded_model, cleaned_text, emails, domains, urls, ips)
        
        print(f"ML analysis completed: probability={probability}")
        
        # Combined risk score
        risk_score, risk_level = combined_score(ruleset_score, probability)
        
        print(f"Final risk assessment: {risk_level} ({risk_score}%)")
        
        # **NEW**: Prepare response data for Flask
        response_data = {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'sus_keywords': keyword_count,
            'cleaned_text': cleaned_text,
            'emails': emails or [],
            'domains': domains or [],
            'urls': urls or [],
            'ips': ips or []
        }
        
        return response_data
        
    except Exception as e:
        print(f"Processing error: {e}")
        return {
            'risk_score': 0,
            'risk_level': 'ERROR',
            'sus_keywords': 0,
            'cleaned_text': f'Processing failed: {str(e)}',
            'emails': [],
            'domains': [],
            'urls': [],
            'ips': []
        }

def combined_score(ruleset_score, probability):
    """Combine ruleset and ML scores (unchanged logic)"""
    # ML score calculation
    ml_score = probability * 100
    print(f"Scores - Ruleset: {ruleset_score}, ML: {ml_score}")
    
    # Combine with 50/50 weightage
    risk_score = round((ruleset_score * 0.5) + (ml_score * 0.5))    
    print(f"Combined risk score: {risk_score}")
    
    # Determine danger level
    if risk_score == 0:
        risk_level = "SAFE"
    elif risk_score <= 33:
        risk_level = "LOW DANGER"
    elif risk_score <= 66:
        risk_level = "MEDIUM DANGER"
    else:
        risk_level = "HIGH DANGER"
    
    return risk_score, risk_level

if __name__ == "__main__":
    main()