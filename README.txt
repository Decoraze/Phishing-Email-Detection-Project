python -m venv venv

venv\Scripts\activate

pip install Flask==2.3.3 Werkzeug==2.3.7 PyPDF2==3.0.1 pdfplumber==0.9.0 beautifulsoup4==4.12.2 extract-msg==0.41.1 pandas==2.0.3 scikit-learn==1.6.0 nltk==3.8.1

python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"

python app.py to start the application

if there are some dependancies not being able to download try:
1) pip install scikit-learn 
2) ctrl shift p --> Python: Select Interpreter --> select the virtual env (venv) that is currently running. 
3) pip install again in the terminal 