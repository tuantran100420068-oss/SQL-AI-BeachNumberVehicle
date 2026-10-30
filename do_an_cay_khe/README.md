# HỆ THỐNG NHẬN DIỆN BIỂN SỐ XE VIỆT NAM

**Nhóm Anh Em Cây Khế** · Đồ án nhận diện biển số xe

## Tổng Quan

Hệ thống nhận diện biển số xe tự động (ALPR - Automatic License Plate Recognition) dành cho biển số xe Việt Nam. Hệ thống dùng **YOLOv8** để phát hiện vị trí biển số trong ảnh và **EasyOCR** để đọc ký tự, sau đó áp dụng luật biển số Việt Nam để sửa lỗi và định dạng kết quả.

**Ngôn ngữ lập trình:** Python 3.10+
**Framework:** Flask (Web), YOLOv8 / Ultralytics (phát hiện), OpenCV (xử lý ảnh), EasyOCR (OCR)
**Phiên bản:** 3.0.0

## Thành Viên Nhóm

| Họ và tên | MSSV |
|-----------|------|
| Trần Đặng Tuân | 24800601028 |

| Họ và tên | MSSV |
|-----------|------|
| Nguyễn Quốc Khánh | 24800612792 |

| Họ và tên | MSSV |
|-----------|------|
| Nguyễn Hải Lâm | 24800600533 |

## Đặc Điểm Nổi Bật

- **Phát hiện bằng YOLOv8:** tìm được nhiều biển số trong cùng một ảnh (tối đa 10).
- **Đọc ký tự bằng EasyOCR:** thử nhiều biến thể ảnh (gốc, xám, threshold, đảo màu) và chọn kết quả tốt nhất.
- **Sửa lỗi theo luật biển số Việt Nam:** 0↔O, 1↔I, 5↔S, 8↔B theo vị trí chữ/số, thêm dấu `-` và `.`.
- **Giao diện web:** kéo thả ảnh, xem trước, xem kết quả được khoanh vùng, xem lịch sử gần đây.
- **API REST:** gọi trực tiếp bằng `curl` hoặc từ ứng dụng khác.

## Công Nghệ Sử Dụng

### Backend
- **Python 3.10+**
- **Flask 3.0.0**: web framework và API
- **Ultralytics (YOLOv8)**: phát hiện biển số
- **OpenCV 4.8.1**: xử lý ảnh
- **EasyOCR 1.7.2**: nhận dạng ký tự
- **NumPy 1.26.2**, **Pillow 10.2.0+**

### Frontend
- HTML5, CSS3, JavaScript ES6+
- Font Awesome, Google Fonts (Inter)

## Cài Đặt

### Yêu Cầu Hệ Thống
- Windows 10/11, Linux hoặc macOS
- Python 3.10 trở lên
- RAM tối thiểu 4GB (khuyến nghị 8GB)
- Ổ cứng trống tối thiểu 2GB (PyTorch, YOLO và model EasyOCR khá nặng)

### Các Bước Cài Đặt

**Bước 1: Tạo môi trường ảo**

Windows:
```
python -m venv .venv
.venv\Scripts\activate
```

Linux/macOS:
```
python3 -m venv .venv
source .venv/bin/activate
```

**Bước 2: Cài thư viện**

```
pip install -r requirements.txt
```

Lần đầu cài có thể mất 10-15 phút vì phải tải PyTorch và model EasyOCR.

**Bước 3: Đặt file trọng số YOLO**

Copy file model YOLO đã train nhận diện biển số vào:

```
models/best.pt
```

Hoặc đặt biến môi trường `PLATE_MODEL_PATH` trỏ tới file `.pt` của bạn.

Windows (CMD):
```
set PLATE_MODEL_PATH=D:\duong\dan\best.pt
```

Linux/macOS:
```
export PLATE_MODEL_PATH=/duong/dan/best.pt
```

**Bước 4: Kiểm tra cài đặt**

```
python -c "import cv2, easyocr, flask, ultralytics; print('Cài đặt thành công!')"
```

## Sử Dụng

### Khởi động server

```
python app.py
```

Server chạy tại: http://localhost:5000

### Sử dụng giao diện web

1. Mở http://localhost:5000
2. Kéo thả ảnh vào vùng upload hoặc bấm "Chọn Từ Máy Tính"
3. Bấm "Bắt Đầu Nhận Diện"
4. Xem biển số được khoanh vùng cùng danh sách kết quả

Định dạng hỗ trợ: PNG, JPG, JPEG, BMP, GIF. Kích thước tối đa: 16MB.

### Sử dụng API

**POST /api/upload**

```
curl -X POST http://localhost:5000/api/upload -F "file=@image.jpg"
```

Kết quả trả về (JSON):
```
{
  "status": "success",
  "message": "Đã nhận diện 1 biển số",
  "count": 1,
  "plates": [
    {
      "license_plate": "59A-12345",
      "confidence": 87.5,
      "bbox": [150, 200, 300, 80]
    }
  ],
  "result_image_base64": "..."
}
```

`bbox` có dạng `[x, y, rộng, cao]` tính bằng pixel.

**GET /api/history**: 10 ảnh kết quả gần nhất.

**GET /health**: kiểm tra trạng thái server.

## Cấu Trúc Thư Mục

```
├── app.py                          # Khởi động ứng dụng Flask
├── config.py                       # Cấu hình
├── requirements.txt                # Thư viện cần cài
├── README.md
│
├── models/
│   ├── __init__.py
│   ├── license_plate_detector.py   # YOLOv8 + EasyOCR + luật biển số VN
│   └── best.pt                     # Trọng số YOLO (bạn tự thêm)
│
├── templates/
│   └── index.html                  # Trang web chính
│
└── static/
    ├── css/style.css
    ├── js/main.js
    └── uploads/                    # Ảnh upload và kết quả
```

## Thuật Toán Hoạt Động

### Giai đoạn 1: Phát hiện biển số bằng YOLOv8
1. Resize ảnh nếu rộng hơn 1920px
2. Chạy YOLOv8, lấy các khung có độ tin cậy từ 0.25 trở lên
3. Sắp theo độ tin cậy, giữ tối đa 10 biển số

### Giai đoạn 2: Tiền xử lý vùng biển số
1. Cắt vùng biển số theo khung YOLO
2. Phóng to nếu chiều cao dưới 100px
3. Lọc nhiễu bằng bilateral filter
4. Tạo các biến thể: ảnh gốc, ảnh xám, adaptive threshold, đảo màu

### Giai đoạn 3: Nhận dạng ký tự bằng EasyOCR
1. Chạy OCR trên từng biến thể, chỉ cho phép ký tự hợp lệ của biển số VN
2. Ghép các dòng từ trên xuống dưới (biển vuông có 2 dòng)
3. Chọn kết quả có độ tin cậy cao nhất

### Giai đoạn 4: Luật biển số Việt Nam
1. Hai ký tự đầu là mã tỉnh (số), ký tự thứ ba là chữ cái series
2. Sửa lỗi nhầm chữ/số theo vị trí
3. Thêm dấu `-` và `.` đúng định dạng
4. Độ tin cậy cuối = trung bình độ tin cậy YOLO và OCR

## Cấu Hình

### Đổi cổng server

Sửa cuối file `app.py`:
```python
app.run(host='0.0.0.0', port=8080, debug=True)
```

### Điều chỉnh tham số nhận diện

Trong `models/license_plate_detector.py`:
```python
LicensePlateDetector(conf_threshold=0.25, use_gpu=False)
```
- `conf_threshold`: ngưỡng tin cậy của YOLO (tăng để bớt nhận nhầm).
- `use_gpu=True`: dùng GPU cho EasyOCR nếu máy có CUDA.

## Xử Lý Sự Cố

**Không tìm thấy file trọng số YOLO.** Chưa có `models/best.pt`. Copy file model vào đó hoặc đặt `PLATE_MODEL_PATH`.

**Lần chạy đầu rất chậm.** EasyOCR đang tải model ngôn ngữ, chỉ xảy ra một lần.

**ModuleNotFoundError.** Chạy lại `pip install -r requirements.txt` trong môi trường ảo đang dùng.

**Cổng 5000 đã được sử dụng.** Windows:
```
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```
Hoặc đổi cổng trong `app.py`.

**Không phát hiện được biển số.** Thử ảnh rõ hơn, góc chụp thẳng hơn, hoặc giảm `conf_threshold`. Nếu vẫn kém, model YOLO có thể cần train thêm với dữ liệu biển số Việt Nam.

**Đọc sai ký tự.** Thường do ảnh mờ, biển bẩn hoặc nghiêng. Chụp lại với ánh sáng tốt hơn.

## Triển Khai Production

Không dùng Flask development server. Ví dụ:

Gunicorn (Linux/macOS):
```
pip install gunicorn
gunicorn -w 1 -b 0.0.0.0:5000 app:app
```

Waitress (Windows):
```
pip install waitress
waitress-serve --port=5000 app:app
```

Mỗi worker tải một bản YOLO và EasyOCR vào RAM, nên giữ số worker thấp.

## Bảo Mật

Trước khi triển khai thật:
1. Đổi `SECRET_KEY` (hiện hard-code trong `app.py`, nên đọc từ biến môi trường như `config.py`)
2. Tắt `debug=True`
3. Thêm xác thực nếu mở ra Internet
4. Dùng HTTPS
5. Định kỳ xóa ảnh cũ trong `static/uploads/`

## Hướng Phát Triển

- Lưu lịch sử nhận diện vào database
- Nhận diện từ video/camera trực tiếp
- Xuất kết quả ra Excel/CSV
- Train thêm YOLO với dữ liệu biển số Việt Nam đa dạng hơn (biển cũ, phai màu, ban đêm)

## Lịch Sử Phiên Bản

### Version 3.0.0
- Quay lại dùng YOLOv8 để phát hiện biển số, kết hợp EasyOCR
- Đổi giao diện sang chủ đề Nhóm Anh Em Cây Khế
- Thêm mục thành viên nhóm

### Version 2.0.0 (28/01/2026)
- Viết lại bằng OpenCV + EasyOCR, không dùng YOLO

### Version 1.0.0
- Phiên bản đầu tiên dùng YOLOv8 + EasyOCR

## Giấy Phép

MIT License.

## Ghi Nhận

Dự án dùng các thư viện mã nguồn mở: Ultralytics YOLOv8, EasyOCR, OpenCV, Flask, NumPy.
