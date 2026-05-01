from flask import Flask, render_template, request, jsonify
import os
import json
from analyzer import analyze_text
from database import init_db, save_analysis, get_all_books, get_book, search_books, delete_book

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Инициализируем базу при старте
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF files allowed'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)
    return jsonify({'success': True, 'filename': file.filename})

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'error': 'No filename'}), 400
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        results = analyze_text(filepath)
        if not results.get("from_cache"):
            book_id = save_analysis(results)
            results['book_id'] = book_id
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Library routes ---

@app.route('/library', methods=['GET'])
def library():
    query = request.args.get('q', '')
    if query:
        books = search_books(query)
    else:
        books = get_all_books()
    return jsonify(books)

@app.route('/library/<int:book_id>', methods=['GET'])
def library_book(book_id):
    book = get_book(book_id)
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    return jsonify(book)

@app.route('/library/<int:book_id>', methods=['DELETE'])
def delete_library_book(book_id):
    delete_book(book_id)
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)