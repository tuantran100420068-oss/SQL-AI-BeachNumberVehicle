"""
Nhận diện biển số xe Việt Nam: YOLOv8 (phát hiện) + EasyOCR (đọc ký tự).

Đặt file trọng số YOLO đã train biển số tại: models/best.pt
(hoặc đặt biến môi trường PLATE_MODEL_PATH trỏ tới file .pt của bạn).
"""
import os
import re

import cv2
import easyocr
import numpy as np
from ultralytics import YOLO

DEFAULT_WEIGHTS = os.path.join(os.path.dirname(__file__), "best.pt")

# Định dạng biển số VN sau khi chuẩn hóa: 59A-1234, 59A-123.45, 59A1-123.45, 30K1-12345
PLATE_PATTERN = re.compile(r"^\d{2}[A-Z][A-Z0-9]?-(\d{4}|\d{3}\.\d{2}|\d{5})$")

# Chỉ nhận kết quả có độ tin cậy từ mức này trở lên (0.6 = 60%). Chỉnh số này nếu cần.
MIN_CONFIDENCE = 0.6


class LicensePlateDetector:
    def __init__(self, weights_path=None, conf_threshold=0.25, use_gpu=False):
        weights_path = weights_path or os.environ.get("PLATE_MODEL_PATH", DEFAULT_WEIGHTS)
        self.conf_threshold = conf_threshold
        if os.path.exists(weights_path):
            print(f"[INFO] Đang tải YOLO: {weights_path}")
            self.yolo = YOLO(weights_path)
        else:
            # Chưa có best.pt: dùng cách phát hiện tạm bằng OpenCV (độ chính xác thấp hơn)
            self.yolo = None
            print("=" * 60)
            print(f"[CẢNH BÁO] Chưa có file YOLO: {weights_path}")
            print("[CẢNH BÁO] Đang dùng chế độ TẠM (OpenCV), kém chính xác hơn YOLO.")
            print("[CẢNH BÁO] Train xong hãy copy best.pt vào thư mục models/ rồi chạy lại.")
            print("=" * 60)
        print("[INFO] Đang khởi tạo EasyOCR...")
        self.reader = easyocr.Reader(["en"], gpu=use_gpu, verbose=False)

    # ------------------------------------------------------------------
    # Phát hiện tạm bằng OpenCV (dùng khi chưa có best.pt)
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_classic(image, max_plates=10):
        """Trả về list (x1, y1, x2, y2, conf) các vùng có dạng biển số."""
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        edges = cv2.Canny(gray, 30, 200)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(closed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        candidates = []
        for c in contours:
            x, y, bw, bh = cv2.boundingRect(c)
            area = bw * bh
            if bh == 0 or area < 2000 or area > 0.3 * w * h:
                continue
            ratio = bw / bh
            if not (1.2 <= ratio <= 5.5):
                continue
            candidates.append((x, y, x + bw, y + bh, area))

        # Loại các khung trùng nhau: ưu tiên khung lớn hơn
        candidates.sort(key=lambda b: -b[4])
        kept = []
        for b in candidates:
            overlap = False
            for k in kept:
                ix = max(0, min(b[2], k[2]) - max(b[0], k[0]))
                iy = max(0, min(b[3], k[3]) - max(b[1], k[1]))
                if ix * iy > 0.4 * min(b[4], k[4]):
                    overlap = True
                    break
            if not overlap:
                kept.append(b)
        return [(b[0], b[1], b[2], b[3], 0.5) for b in kept[:max_plates]]

    # ------------------------------------------------------------------
    # Tiền xử lý vùng biển số cho OCR
    # ------------------------------------------------------------------
    @staticmethod
    def _prepare_variants(crop):
        # Thêm lề để chữ sát mép không bị cắt, rồi phóng to cho EasyOCR đọc rõ
        crop = cv2.copyMakeBorder(crop, 6, 6, 6, 6, cv2.BORDER_REPLICATE)
        h, w = crop.shape[:2]
        if h < 120:
            scale = 120 / h
            crop = cv2.resize(crop, (int(w * scale), 120), interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        # Tăng tương phản cục bộ (CLAHE) giúp biển tối/phản sáng
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
        )
        return [crop, gray, clahe, thresh, cv2.bitwise_not(thresh)]

    def _read_plate(self, crop):
        """Chạy OCR trên nhiều biến thể, trả về (text, confidence) tốt nhất."""
        best_text, best_conf = "", 0.0
        for img in self._prepare_variants(crop):
            results = self.reader.readtext(
                img,
                allowlist="ABCDEFGHKLMNPRSTUVXYZ0123456789-. ",
                paragraph=False,
            )
            if not results:
                continue
            # Ghép các dòng từ trên xuống dưới (biển vuông có 2 dòng)
            results.sort(key=lambda r: (r[0][0][1], r[0][0][0]))
            text = "".join(r[1] for r in results)
            conf = float(np.mean([r[2] for r in results]))
            if conf > best_conf and len(text) >= 5:
                best_text, best_conf = text, conf
        return best_text, best_conf

    # ------------------------------------------------------------------
    # Luật biển số Việt Nam
    # ------------------------------------------------------------------
    @staticmethod
    def _to_digit(c):
        return {"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1",
                "S": "5", "B": "8", "Z": "2", "G": "6"}.get(c, c)

    @staticmethod
    def _to_letter(c):
        return {"0": "O", "1": "I", "5": "S", "8": "B", "2": "Z", "6": "G"}.get(c, c)

    def apply_vietnam_license_plate_rules(self, raw):
        text = re.sub(r"[^A-Z0-9]", "", raw.upper())
        if len(text) < 7 or len(text) > 10:
            return text or raw

        # 2 ký tự đầu: mã tỉnh (số)
        province = "".join(self._to_digit(c) for c in text[:2])
        # Ký tự thứ 3: chữ cái series
        series = self._to_letter(text[2])
        rest = text[3:]

        # Ô tô cũ / xe máy có thêm 1 ký tự thứ 4 (chữ hoặc số): 30K1-12345, 59A1-123.45
        extra = ""
        if len(rest) == 6:
            extra, rest = rest[0], rest[1:]
        digits = "".join(self._to_digit(c) for c in rest)

        if len(digits) == 5:
            # Biển 5 số (xe máy, ô tô) viết dạng 123.45
            body = f"{digits[:3]}.{digits[3:]}"
        elif len(digits) == 4:
            body = digits
        else:
            return f"{province}{series}{extra}-{digits}"
        return f"{province}{series}{extra}-{body}"

    # ------------------------------------------------------------------
    # API chính
    # ------------------------------------------------------------------
    def detect_multiple(self, image_path, max_plates=10):
        """
        Trả về (output_image, plates_list, status, message)
        plates_list: [{'plate': str, 'confidence': float 0-1, 'bbox': [x, y, w, h]}]
        """
        image = cv2.imread(image_path)
        if image is None:
            return None, [], "error", "Không đọc được ảnh"

        # Resize nếu ảnh quá lớn
        h, w = image.shape[:2]
        if w > 1920:
            scale = 1920 / w
            image = cv2.resize(image, (1920, int(h * scale)))

        # Lấy danh sách khung biển số: YOLO nếu có best.pt, ngược lại dùng OpenCV tạm
        if self.yolo is not None:
            result = self.yolo.predict(image, conf=self.conf_threshold, verbose=False)[0]
            boxes = result.boxes
            detections = []
            if boxes is not None and len(boxes) > 0:
                order = np.argsort(-boxes.conf.cpu().numpy())[:max_plates]
                for i in order:
                    bx1, by1, bx2, by2 = boxes.xyxy[i].cpu().numpy().astype(int)
                    detections.append((int(bx1), int(by1), int(bx2), int(by2), float(boxes.conf[i])))
        else:
            detections = self._detect_classic(image, max_plates)

        if not detections:
            return image, [], "no_plate", "Không phát hiện được biển số"

        output = image.copy()
        plates = []

        for x1, y1, x2, y2, det_conf in detections:
            x1, y1 = max(x1, 0), max(y1, 0)
            crop = image[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            raw_text, ocr_conf = self._read_plate(crop)
            plate_text = self.apply_vietnam_license_plate_rules(raw_text) if raw_text else ""

            # Không đọc được chữ thì bỏ qua, không vẽ khung
            if not plate_text:
                continue
            # Chế độ tạm (OpenCV) hay khoanh nhầm lưới xe, đèn xe...:
            # chỉ nhận khi chữ đọc ra khớp định dạng biển số Việt Nam
            if self.yolo is None and not PLATE_PATTERN.match(plate_text):
                continue

            # Độ tin cậy: có YOLO thì lấy trung bình (YOLO + OCR); chế độ tạm thì chỉ dùng OCR
            # (vì chế độ tạm không có điểm tin cậy thật cho phần tìm khung)
            if self.yolo is not None:
                confidence = (det_conf + ocr_conf) / 2 if ocr_conf else det_conf
            else:
                confidence = ocr_conf
            if confidence < MIN_CONFIDENCE:
                continue

            cv2.rectangle(output, (x1, y1), (x2, y2), (0, 255, 0), 3)
            label = plate_text
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
            cv2.rectangle(output, (x1, max(y1 - th - 12, 0)), (x1 + tw + 8, y1), (0, 255, 0), -1)
            cv2.putText(output, label, (x1 + 4, max(y1 - 6, th)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
            plates.append({
                "plate": plate_text,
                "confidence": confidence,
                "bbox": [int(x1), int(y1), int(x2 - x1), int(y2 - y1)],
            })

        if not plates:
            return output, [], "no_plate", "Phát hiện vùng biển số nhưng không đọc được ký tự"
        return output, plates, "success", f"Đã nhận diện {len(plates)} biển số"