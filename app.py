from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
import cv2
import pytesseract
import requests
import os
from PIL import Image
import time
import uuid

app = Flask(__name__)
app.secret_key = "book_scanner_secret_key"

# Create uploads directory if it doesn't exist
os.makedirs('uploads', exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/camera')
def camera():
    return render_template('camera.html')

# Add this route for the upload page
@app.route('/upload_page')
def upload_page():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        flash('No file selected')
        return redirect(url_for('index'))
    
    image_file = request.files['image']
    
    if image_file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    # Generate a unique filename to prevent overwriting
    filename = f"{uuid.uuid4()}_{image_file.filename}"
    image_path = os.path.join('uploads', filename)
    image_file.save(image_path)

    # Process the image
    extracted_text = extract_text_from_image(image_path)
    book_info = search_book_info(extracted_text)
    
    return render_template('results.html', 
                          image_path=image_path,
                          extracted_text=extracted_text,
                          book_info=book_info)

@app.route('/process_camera', methods=['POST'])
def process_camera():
    if 'image_data' not in request.form:
        flash('No image captured')
        return redirect(url_for('camera'))
    
    # Get the base64 image data from the form
    image_data = request.form['image_data']
    
    # Convert base64 to image and save
    import base64
    image_data = image_data.replace('data:image/jpeg;base64,', '')
    image_bytes = base64.b64decode(image_data)
    
    # Save the image
    filename = f"camera_capture_{uuid.uuid4()}.jpg"
    image_path = os.path.join('uploads', filename)
    
    with open(image_path, 'wb') as f:
        f.write(image_bytes)
    
    # Process the image
    extracted_text = extract_text_from_image(image_path)
    book_info = search_book_info(extracted_text)
    
    return render_template('results.html', 
                          image_path=image_path,
                          extracted_text=extracted_text,
                          book_info=book_info)

def extract_text_from_image(image_path):
    """Extract text from an image using OCR"""
    try:
        # Open image with PIL
        image = Image.open(image_path)
        
        # Use pytesseract for OCR
        extracted_text = pytesseract.image_to_string(image)
        return extracted_text.strip()
    except Exception as e:
        print(f"OCR error: {str(e)}")
        return "Error: Could not extract text from image."

def search_book_info(title):
    """Search for book information using Google Books API"""
    try:
        if not title or len(title) < 3:
            return None
            
        # Clean the title for URL
        query = title.replace(' ', '+')
        
        # Query Google Books API
        api_url = f"https://www.googleapis.com/books/v1/volumes?q={query}"
        response = requests.get(api_url)
        
        if response.status_code != 200:
            print(f"API error: {response.status_code}")
            return None
        
        book_data = response.json()
        
        if book_data.get('totalItems', 0) > 0:
            # Get the first matching book
            book = book_data['items'][0]['volumeInfo']
            
            result = {
                'title': book.get('title', 'Unknown Title'),
                'authors': ', '.join(book.get('authors', ['Unknown Author'])),
                'summary': book.get('description', 'No description available'),
                'cover': book.get('imageLinks', {}).get('thumbnail', None)
            }
            return result
        else:
            print("No books found matching this title.")
            return None
    except Exception as e:
        print(f"Book search error: {str(e)}")
        return None

if __name__ == '__main__':
    app.run(debug=True)