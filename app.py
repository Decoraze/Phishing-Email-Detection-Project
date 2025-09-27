from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import os
import time
import json
import uuid
import threading

# Import our email processor
try:
    from text_processor import process_email_text, get_processor
    PROCESSOR_AVAILABLE = True
    print("✓ Email processor loaded successfully")
except ImportError as e:
    print(f"✗ Failed to load email processor: {e}")
    PROCESSOR_AVAILABLE = False
    
    def process_email_text(text, debug=False):
        return f"Error: Could not load email processor - {e}"

# **NEW**: Session storage for processing status
session_data = {}
session_lock = threading.Lock()

def get_latest_processed_text():
    """Function for external programs to get the latest processed text."""
    global latest_processed_text
    return latest_processed_text

def get_processing_queue():
    """Get all recent processed texts with metadata."""
    global processing_queue
    return processing_queue.copy()

def clear_processing_queue():
    """Clear the processing queue."""
    global processing_queue, latest_processed_text, latest_risk_analysis
    processing_queue.clear()
    latest_processed_text = ""
    latest_risk_analysis = {}
    print("Processing queue cleared")

# Create the Flask application
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-in-production')
app.config.update({
    'MAX_CONTENT_LENGTH': 1 * 1024 * 1024,  # 1MB limit
    'SEND_FILE_MAX_AGE_DEFAULT': 31536000
})

# Global variables for pipeline access (unchanged)
latest_processed_text = ""
latest_risk_analysis = {}
processing_queue = []

# Statistics tracking (unchanged)
request_stats = {
    'total_requests': 0,
    'total_processing_time': 0,
    'average_text_length': 0,
    'max_text_length': 0
}

def store_processed_text(processed_text: str, original_length: int, processing_time: float):
    """Store processed text for external pipeline access (unchanged)"""
    global latest_processed_text, processing_queue
    
    latest_processed_text = processed_text
    
    processing_queue.append({
        'text': processed_text,
        'timestamp': time.perf_counter(),
        'original_length': original_length,
        'processed_length': len(processed_text),
        'processing_time': processing_time
    })
    
    if len(processing_queue) > 10:
        processing_queue.pop(0)
    
    # Save to file for cross-process access
    try:
        with open('processed_text.txt', 'w', encoding='utf-8') as f:
            f.write(processed_text)
        
        metadata = {
            'timestamp': time.time(),
            'original_length': original_length,
            'processed_length': len(processed_text),
            'processing_time': processing_time
        }
        with open('processing_metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✓ Processed text stored: {len(processed_text)} characters")
        
    except Exception as e:
        print(f"Warning: Could not save to files: {e}")

def store_risk_analysis(risk_data: dict):
    """Store risk analysis results for display (unchanged)"""
    global latest_risk_analysis
    latest_risk_analysis = risk_data
    print(f"✓ Risk analysis stored: {risk_data.get('risk_level', 'Unknown')} - {risk_data.get('risk_score', 0)}%")

@app.before_request
def before_request():
    """Track request timing (unchanged)"""
    request.start_time = time.perf_counter()

@app.after_request
def after_request(response):
    """Update statistics (unchanged)"""
    if hasattr(request, 'start_time'):
        processing_time = time.perf_counter() - request.start_time
        request_stats['total_requests'] += 1
        request_stats['total_processing_time'] += processing_time
    return response

@app.route('/')
def index():
    """Main page route (unchanged)"""
    return render_template('index.html')

# **NEW**: Modified route to redirect to buffer
@app.route('/process', methods=['POST'])
def process_text():
    """Handle form submission and redirect to buffer page"""
    try:
        processing_start = time.perf_counter()
        text_content = request.form.get('text_input', '').strip()
        
        if not text_content:
            flash('Please enter some email text to process.', 'error')
            return redirect(url_for('index'))
        
        # Update statistics
        text_length = len(text_content)
        request_stats['max_text_length'] = max(request_stats['max_text_length'], text_length)
        
        total_requests = request_stats['total_requests']
        if total_requests > 0:
            current_avg = request_stats['average_text_length']
            request_stats['average_text_length'] = (
                (current_avg * (total_requests - 1) + text_length) / total_requests
            )
        else:
            request_stats['average_text_length'] = text_length
        
        # **NEW**: Create unique session ID
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        session['input_text'] = text_content[:500] + ('...' if len(text_content) > 500 else '')
        
        # **NEW**: Store session data
        with session_lock:
            session_data[session_id] = {
                'status': 'processing',
                'input_text': text_content,
                'result': None,
                'timestamp': time.time()
            }
        
        # Process basic email text first
        if PROCESSOR_AVAILABLE:
            clean_text = process_email_text(text_content, debug=False)
        else:
            clean_text = "Error: Email processor not available"
        
        processing_time = time.perf_counter() - processing_start
        store_processed_text(clean_text, text_length, processing_time)
        
        # **NEW**: Store initial processed text in session
        with session_lock:
            session_data[session_id]['clean_text'] = clean_text
            session_data[session_id]['processing_time'] = processing_time
            session_data[session_id]['input_length'] = text_length
        
        print(f"Session {session_id[:8]} created, redirecting to buffer")
        
        # **NEW**: Redirect to buffer page instead of results
        return redirect(url_for('buffer'))
    
    except Exception as e:
        flash(f'Error processing text: {str(e)}', 'error')
        return redirect(url_for('index'))

# **NEW**: Buffer page route
@app.route('/buffer')
def buffer():
    """Show buffer/loading page"""
    session_id = session.get('session_id')
    if not session_id or session_id not in session_data:
        flash('Session expired. Please try again.', 'error')
        return redirect(url_for('index'))
    
    return render_template('buffer.html', session_id=session_id)

# **NEW**: Status checking endpoint
@app.route('/check_status')
def check_status():
    """Check processing status for current session"""
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'No session found'})
    
    with session_lock:
        data = session_data.get(session_id, {})
    
    if not data:
        return jsonify({'error': 'Session not found'})
    
    status = data.get('status', 'unknown')
    
    if status == 'completed':
        return jsonify({
            'status': 'completed',
            'redirect': True
        })
    else:
        return jsonify({
            'status': status,
            'redirect': False
        })

# **NEW**: Results page with session validation
@app.route('/result')
def result():
    """Show results page with session data"""
    session_id = session.get('session_id')
    if not session_id:
        flash('Session expired. Please try again.', 'error')
        return redirect(url_for('index'))
    
    with session_lock:
        data = session_data.get(session_id, {})
    
    if not data or data.get('status') != 'completed':
        return redirect(url_for('buffer'))
    
    # Get data from session
    result_data = data.get('result', {})
    clean_text = data.get('clean_text', '')
    original_text = session.get('input_text', '')
    processing_time = data.get('processing_time', 0)
    input_length = data.get('input_length', 0)
    
    # Extract risk analysis
    risk_analysis = {
        'risk_score': result_data.get('risk_score', 0),
        'risk_level': result_data.get('risk_level', 'Unknown'),
        'sus_keywords': result_data.get('sus_keywords', 0)
    }
    
    flash('Email analysis completed successfully!', 'success')
    
    return render_template('result.html',
                         original_text=original_text,
                         result=clean_text,
                         processing_time=f"{processing_time:.4f}s",
                         input_length=f"{input_length:,} characters",
                         output_length=f"{len(clean_text):,} characters",
                         throughput=f"{input_length / processing_time / 1000:.1f} KB/s" if processing_time > 0 else "N/A",
                         risk_analysis=risk_analysis)

# **MODIFIED**: API endpoints for main.py integration
@app.route('/api/get_latest', methods=['GET'])
def get_latest():
    """Get latest processed text for main.py"""
    # Find most recent processing session
    with session_lock:
        latest_session = None
        latest_time = 0
        
        for sid, data in session_data.items():
            if data.get('status') == 'processing' and data.get('timestamp', 0) > latest_time:
                latest_session = data
                latest_time = data.get('timestamp', 0)
    
    if latest_session and latest_session.get('input_text'):
        return jsonify({
            'success': True,
            'text': latest_session['input_text']
        })
    else:
        return jsonify({
            'success': False,
            'message': 'No processed text available'
        })

# **NEW**: API endpoint for main.py to update results
@app.route('/api/update_results', methods=['POST'])
def update_results():
    """Receive results from main.py processing"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'JSON required'})
        
        result_data = request.get_json()
        
        # **NEW**: Update the processing session with results
        with session_lock:
            # Find the session that's currently processing
            for session_id, data in session_data.items():
                if data.get('status') == 'processing':
                    data['status'] = 'completed'
                    data['result'] = result_data
                    print(f"Session {session_id[:8]} completed with ML results")
                    break
        
        # Also update global variables for compatibility
        store_risk_analysis(result_data)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Existing API endpoints (unchanged)
@app.route('/api/process', methods=['POST'])
def api_process():
    """API endpoint that returns processed text (unchanged)"""
    try:
        processing_start = time.perf_counter()
        
        if request.is_json:
            data = request.get_json()
            text_content = data.get('text', '')
        else:
            text_content = request.form.get('text', '')
        
        if not text_content.strip():
            return "No text provided", 400
        
        text_length = len(text_content)
        
        if PROCESSOR_AVAILABLE:
            clean_text = process_email_text(text_content.strip(), debug=False)
        else:
            clean_text = "Error: Processor not available"
        
        processing_time = time.perf_counter() - processing_start
        store_processed_text(clean_text, text_length, processing_time)
        
        return clean_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/api/process_detailed', methods=['POST'])
def api_process_detailed():
    """API endpoint with detailed metadata (unchanged)"""
    try:
        processing_start = time.perf_counter()
        
        if request.is_json:
            data = request.get_json()
            text_content = data.get('text', '')
        else:
            text_content = request.form.get('text', '')
        
        if not text_content.strip():
            return jsonify({'success': False, 'error': 'No text provided'})
        
        text_content = text_content.strip()
        text_length = len(text_content)
        
        if PROCESSOR_AVAILABLE:
            processor = get_processor()
            clean_text = processor.process_text(text_content, debug=False)
            stats = processor.get_performance_stats()
        else:
            clean_text = "Error: Processor not available"
            stats = {}
        
        processing_time = time.perf_counter() - processing_start
        store_processed_text(clean_text, text_length, processing_time)
        
        return jsonify({
            'success': True,
            'input_length': text_length,
            'output_length': len(clean_text),
            'result': clean_text,
            'processing_time': f"{processing_time:.4f}s",
            'throughput_kbps': text_length / processing_time / 1000 if processing_time > 0 else 0,
            'processor_stats': stats,
            'stored_for_pipeline': True
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/get_latest_with_risk', methods=['GET'])
def get_latest_with_risk():
    """Get latest processed text with risk analysis (unchanged)"""
    global latest_processed_text, latest_risk_analysis
    
    return jsonify({
        'success': True,
        'text': latest_processed_text,
        'risk_analysis': latest_risk_analysis,
        'timestamp': time.time()
    })

@app.route('/api/get_queue', methods=['GET'])
def get_queue():
    """Get processing queue (unchanged)"""
    global processing_queue
    
    return jsonify({
        'success': True,
        'count': len(processing_queue),
        'items': processing_queue
    })

@app.route('/api/clear_queue', methods=['POST'])
def clear_queue():
    """Clear processing queue (unchanged)"""
    clear_processing_queue()
    return jsonify({
        'success': True,
        'message': 'Processing queue cleared'
    })

@app.route('/stats')
def performance_stats():
    """Performance statistics (unchanged)"""
    try:
        avg_processing_time = (
            request_stats['total_processing_time'] / request_stats['total_requests']
            if request_stats['total_requests'] > 0 else 0
        )
        
        processor_stats = {}
        if PROCESSOR_AVAILABLE:
            processor = get_processor()
            processor_stats = processor.get_performance_stats()
        
        return jsonify({
            'application_stats': {
                'total_requests': request_stats['total_requests'],
                'average_processing_time': f"{avg_processing_time:.4f}s",
                'average_text_length': f"{request_stats['average_text_length']:.0f} chars",
                'max_text_length': f"{request_stats['max_text_length']:,} chars"
            },
            'processor_stats': processor_stats,
            'processor_available': PROCESSOR_AVAILABLE,
            'latest_risk_analysis': latest_risk_analysis
        })
    
    except Exception as e:
        return jsonify({'error': str(e)})

# Error handlers (unchanged)
@app.errorhandler(413)
def too_large(e):
    flash('Text input is too large. Maximum size is 1MB.', 'error')
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    flash('An internal error occurred. Please try again.', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    try:
        print("=" * 60)
        print("Email Processor with Session Buffer System")
        print("=" * 60)
        print(f"Processor available: {'✓ Yes' if PROCESSOR_AVAILABLE else '✗ No'}")
        print("Web Interface: http://localhost:5000")
        print("Performance Stats: http://localhost:5000/stats")
        print()
        print("NEW FLOW:")
        print("  1. User submits form → creates session → redirects to buffer")
        print("  2. Buffer page polls status every second")
        print("  3. main.py processes ML → updates session via API")
        print("  4. Buffer redirects to results when complete")
        print("=" * 60)
        
        app.run(debug=True, host='0.0.0.0', port=5000)
        
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Failed to start Flask application: {e}")
    finally:
        print("Application stopped.")