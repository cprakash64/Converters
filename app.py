from flask import Flask, render_template, request, send_file
from PIL import Image
from pdf2image import convert_from_bytes, convert_from_path
import io
import os
import tempfile
import subprocess
import logging

app = Flask(__name__)

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/imagetopdf')
def upload_file():
    # Ensure your HTML form allows for multiple file uploads and includes AVIF/HEIC if needed
    return render_template("image_upload.html")
    
@app.route('/imagetopdf', methods=['POST'])
def convert_to_pdf():
    files = request.files.getlist('file')  # Adjust the form to allow multiple file uploads
    if not files:
        return 'No files selected for uploading', 400
    
    images = []
    for file in files:
        if file and allowed_image_file(file.filename):
            try:
                # Initial image handling for supported formats by Pillow
                image = Image.open(file.stream)
                if image.mode == "RGBA":
                    image = image.convert("RGB")
                images.append(image)
            except Exception as e:
                return f'Error processing file {file.filename}: {str(e)}', 500
        else:
            return f'Invalid file format for file {file.filename}. Only JPG, JPEG, PNG, WEBP, AVIF, and HEIC files are allowed.', 400
    
    if images:
        # Save all images to a PDF
        pdf_io = io.BytesIO()
        images[0].save(pdf_io, 'PDF', save_all=True, append_images=images[1:], quality=100)
        pdf_io.seek(0)
        return send_file(pdf_io, mimetype='application/pdf', as_attachment=True, download_name='converted.pdf')
    else:
        return 'No valid images to convert', 400

def allowed_image_file(filename):
    # Extend to include webp, avif, and heic if you have handling for them
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg', 'png', 'webp', 'avif', 'heic'}


@app.route('/pdftoimage')
def pdftoimage():
    return render_template('pdf_upload.html')

@app.route('/pdftoimage', methods=['POST'])
def convert_pdf_to_image():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    
    format_selected = request.form.get('format', 'jpg')  # Retrieve the selected format
    
    if file and allowed_pdf_file(file.filename):
        try:
            images_from_bytes = convert_from_bytes(file.read(), last_page=1, first_page=0)
            if images_from_bytes:
                img = images_from_bytes[0]
                img_io = io.BytesIO()
                
                # Determine the image format and MIME type based on user selection
                if format_selected == 'png':
                    img.save(img_io, 'PNG', quality=100)
                    mimetype = 'image/png'
                    download_name = 'converted.png'
                elif format_selected == 'jpeg':
                    img.save(img_io, 'JPEG', quality=100)
                    mimetype = 'image/jpeg'
                    download_name = 'converted.jpeg'
                else:  # Default to JPG
                    img.save(img_io, 'JPEG', quality=100)
                    mimetype = 'image/jpeg'
                    download_name = 'converted.jpg'
                
                img_io.seek(0)
                return send_file(img_io, mimetype=mimetype, as_attachment=True, download_name=download_name)
            else:
                return 'Conversion failed', 500
        except Exception as e:
            return f'Error during conversion: {str(e)}'
    else:
        return 'Invalid file type', 400

def allowed_pdf_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() == 'pdf'


@app.route('/webptojpg')
def webptojpg():
    return render_template('webp_upload.html')

@app.route('/webptojpg', methods=['POST'])
def convert_webp():
    if 'file' not in request.files:
        return 'No file part in the request', 400
    file = request.files['file']
    format_selected = request.form.get('format', 'jpg')  # Retrieve the selected format
    if file.filename == '':
        return 'No file selected for uploading', 400
    
    # Call allowed_file with 'webp' as allowed extension
    if file and allowed_file(file.filename, {'webp'}):
        try:
            image = Image.open(file.stream).convert("RGB")
            output = io.BytesIO()
            
            # Adjust the conversion logic based on the selected format
            if format_selected == 'png':
                image.save(output, format='PNG')
                mimetype = 'image/png'
                download_name = 'converted.png'
            elif format_selected == 'jpeg':
                image.save(output, format='JPEG')
                mimetype = 'image/jpeg'
                download_name = 'converted.jpeg'
            else:  # Default to JPG
                image.save(output, format='JPEG')
                mimetype = 'image/jpeg'
                download_name = 'converted.jpg'
            
            output.seek(0)
            return send_file(output, mimetype=mimetype, as_attachment=True, download_name=download_name)
        except Exception as e:
            return f'Error converting file: {str(e)}', 500
    else:
        return 'Invalid file format. Only WEBP files are allowed.', 400

def allowed_file(filename, allowed_extensions):
    # Now expects a set of allowed extensions as a parameter
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/heictojpg')
def heictojpg():
    return render_template('heic_upload.html')

@app.route('/heictojpg', methods=['POST'])
def convert_heic():
    if 'file' not in request.files:
        return 'No file part in the request', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file for uploading', 400
    
    selected_format = request.form.get('format', 'jpg')  # Default to JPG if no selection is made
    
    if file and allowed_heic_file(file.filename):
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=True, suffix='.heic') as temp_heic:
                file.save(temp_heic.name)
                
                # Prepare output filename based on selected format
                output_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{selected_format}')
                output_file.close()
                
                # Use ImageMagick to convert HEIC to selected format
                subprocess.run(['magick', 'convert', temp_heic.name, output_file.name], check=True)
                
                # Send the converted file
                return send_file(output_file.name, mimetype=f'image/{selected_format}', as_attachment=True, download_name=f'converted.{selected_format}')
        except subprocess.CalledProcessError as e:
            return f'Error converting file: {str(e)}', 500
        finally:
            # Ensure temporary files are cleaned up
            if os.path.exists(output_file.name):
                os.remove(output_file.name)
    else:
        return 'Invalid file format. Only HEIC files are allowed.', 400

def allowed_heic_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() == 'heic'

# Setup basic logging
logging.basicConfig(level=logging.INFO)

@app.route('/aviftojpg')
def aviftojpg():
    return render_template("avif_upload.html")

@app.route('/aviftojpg', methods=['POST'])
def convert_avif():
    logging.info("Starting conversion process")
    if 'file' not in request.files:
        logging.error("No file part in the request")
        return 'No file part in the request', 400
    file = request.files['file']
    format_selected = request.form.get('format', 'jpg')

    if file.filename == '':
        logging.error("No file selected for uploading")
        return 'No file selected for uploading', 400

    if file and allowed_file(file.filename, ['avif']):
        try:
            with tempfile.NamedTemporaryFile(delete=True, suffix='.avif') as tmp_avif:
                file.save(tmp_avif.name)

                output_png_path = tempfile.mktemp(suffix='.png') # Temporary file for the PNG output
                command = ['ffmpeg', '-i', tmp_avif.name, output_png_path]
                logging.info(f"Running command: {' '.join(command)}")
                subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                pil_image = Image.open(output_png_path)

                output = io.BytesIO()
                if format_selected == 'png':
                    pil_image.save(output, format='PNG')
                    mimetype = 'image/png'
                    download_name = 'converted.png'
                elif format_selected == 'jpeg':
                    pil_image.save(output, format='JPEG')
                    mimetype = 'image/jpeg'
                    download_name = 'converted.jpeg'
                else:
                    pil_image.save(output, format='JPEG')
                    mimetype = 'image/jpeg'
                    download_name = 'converted.jpg'
                output.seek(0)

                os.remove(output_png_path) # Clean up the temporary PNG file
                logging.info("Conversion successful")
                return send_file(output, mimetype=mimetype, as_attachment=True, download_name=download_name)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error converting file with FFmpeg: {e}")
            return f'Error converting file with FFmpeg: {e}', 500
        except Exception as e:
            logging.error(f"Error during conversion: {e}")
            return f'Error during conversion: {e}', 500
    else:
        logging.error("Invalid file format. Only AVIF files are allowed.")
        return 'Invalid file format. Only AVIF files are allowed.', 400

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


if __name__ == '__main__':
    app.run(debug=True)
