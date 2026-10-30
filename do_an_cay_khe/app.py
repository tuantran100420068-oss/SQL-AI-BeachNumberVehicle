from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import cv2
import base64
from datetime import datetime
from models.license_plate_detector import LicensePlateDetector

app = Flask(__name__)

# Cấu hình
app.config['SECRET_KEY'] = 'your-secret-key-here'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'bmp', 'gif'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Khởi tạo detector
detector = LicensePlateDetector()

def allowed_file(filename):
    """Kiểm tra file có hợp lệ không"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def encode_image_to_base64(image_path):
    """Chuyển ảnh thành base64 để gửi về frontend"""
    try:
        with open(image_path, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return encoded_string
    except:
        return None

@app.route('/')
def index():
    """Trang chủ"""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """API upload và xử lý ảnh - HỖ TRỢ NHIỀU BIỂN SỐ"""
    try:
        # Kiểm tra file
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'Không tìm thấy file trong request'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'Chưa chọn file'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'status': 'error',
                'message': 'Định dạng file không được hỗ trợ. Vui lòng chọn file ảnh (PNG, JPG, JPEG, BMP)'
            }), 400
        
        # Lưu file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Tự động nhận diện TẤT CẢ biển số trong ảnh
        output_image, plates_list, status, message = detector.detect_multiple(filepath, max_plates=10)
        
        # Lưu ảnh kết quả
        output_filename = f"result_{filename}"
        output_filepath = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        if output_image is not None:
            cv2.imwrite(output_filepath, output_image)
        else:
            output_filepath = filepath
        
        result_image_base64 = encode_image_to_base64(output_filepath)
        
        # Format response
        response_data = {
            'status': status,
            'message': message,
            'mode': 'multiple',
            'count': len(plates_list),
            'plates': [
                {
                    'license_plate': p['plate'],
                    'confidence': round(p['confidence'] * 100, 2),
                    'bbox': p['bbox']
                }
                for p in plates_list
            ],
            'original_image': f'/static/uploads/{filename}',
            'result_image': f'/static/uploads/{output_filename}',
            'result_image_base64': result_image_base64
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Lỗi xử lý: {str(e)}'
        }), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """API lấy lịch sử nhận diện """
    try:
        uploads_dir = app.config['UPLOAD_FOLDER']
        files = os.listdir(uploads_dir)
        
        # Lọc file kết quả và sắp xếp theo thời gian
        result_files = [f for f in files if f.startswith('result_')]
        result_files.sort(reverse=True)
        
        history = []
        for filename in result_files[:10]:  # Lấy 10 kết quả gần nhất
            history.append({
                'filename': filename,
                'url': f'/static/uploads/{filename}',
                'timestamp': filename.split('_')[1] if '_' in filename else ''
            })
        
        return jsonify({
            'status': 'success',
            'history': history
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Server đang hoạt động'
    }), 200

@app.errorhandler(413)
def too_large(e):
    """Xử lý lỗi file quá lớn"""
    return jsonify({
        'status': 'error',
        'message': 'File quá lớn. Kích thước tối đa là 16MB'
    }), 413

@app.errorhandler(404)
def not_found(e):
    """Xử lý lỗi 404"""
    return jsonify({
        'status': 'error',
        'message': 'Không tìm thấy trang'
    }), 404

@app.errorhandler(500)
def server_error(e):
    """Xử lý lỗi 500"""
    return jsonify({
        'status': 'error',
        'message': 'Lỗi server'
    }), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 KHỞI ĐỘNG SERVER NHẬN DIỆN BIỂN SỐ XE")
    print("=" * 60)
    print("📡 Server đang chạy tại: http://localhost:5000")
    print("🌐 Mở trình duyệt và truy cập: http://localhost:5000")
    print("⏹️  Nhấn Ctrl+C để dừng server")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
