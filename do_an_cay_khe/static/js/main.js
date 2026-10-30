(() => {
    const $ = (id) => document.getElementById(id);
    const dropZone = $('dropZone');
    const fileInput = $('fileInput');
    const chooseBtn = $('chooseBtn');
    const previewBox = $('previewBox');
    const previewImg = $('previewImg');
    const detectBtn = $('detectBtn');
    const resetBtn = $('resetBtn');
    const loading = $('loading');
    const errorBox = $('errorBox');
    const resultSection = $('resultSection');
    const resultMessage = $('resultMessage');
    const resultImg = $('resultImg');
    const plateList = $('plateList');
    const historyBox = $('history');

    const MAX_SIZE = 16 * 1024 * 1024;
    const ALLOWED = ['image/png', 'image/jpeg', 'image/bmp', 'image/gif'];
    let selectedFile = null;

    const show = (el) => el.classList.remove('hidden');
    const hide = (el) => el.classList.add('hidden');

    function showError(msg) {
        errorBox.textContent = msg;
        show(errorBox);
    }

    function handleFile(file) {
        hide(errorBox);
        hide(resultSection);
        if (!file) return;
        if (!ALLOWED.includes(file.type)) {
            return showError('Định dạng không hỗ trợ. Vui lòng chọn PNG, JPG, JPEG, BMP hoặc GIF.');
        }
        if (file.size > MAX_SIZE) {
            return showError('File quá lớn. Kích thước tối đa là 16MB.');
        }
        selectedFile = file;
        previewImg.src = URL.createObjectURL(file);
        hide(dropZone);
        show(previewBox);
    }

    function reset() {
        selectedFile = null;
        fileInput.value = '';
        hide(previewBox);
        hide(errorBox);
        hide(resultSection);
        show(dropZone);
    }

    chooseBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => handleFile(e.target.files[0]));
    resetBtn.addEventListener('click', reset);

    ['dragenter', 'dragover'].forEach((ev) =>
        dropZone.addEventListener(ev, (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        })
    );
    ['dragleave', 'drop'].forEach((ev) =>
        dropZone.addEventListener(ev, (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        })
    );
    dropZone.addEventListener('drop', (e) => handleFile(e.dataTransfer.files[0]));

    detectBtn.addEventListener('click', async () => {
        if (!selectedFile) return;
        hide(errorBox);
        hide(resultSection);
        show(loading);
        detectBtn.disabled = true;

        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            const res = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (!res.ok || data.status === 'error') {
                throw new Error(data.message || 'Có lỗi xảy ra');
            }
            renderResult(data);
            loadHistory();
        } catch (err) {
            showError(err.message);
        } finally {
            hide(loading);
            detectBtn.disabled = false;
        }
    });

    function renderResult(data) {
        resultMessage.textContent = data.message;
        resultImg.src = data.result_image_base64
            ? `data:image/jpeg;base64,${data.result_image_base64}`
            : data.result_image;

        plateList.innerHTML = '';
        (data.plates || []).forEach((p) => {
            const item = document.createElement('div');
            item.className = 'plate-item';

            const num = document.createElement('div');
            num.className = 'plate-number';
            num.textContent = p.license_plate;

            const conf = document.createElement('div');
            conf.className = 'plate-conf';
            conf.textContent = `Độ tin cậy: ${p.confidence}%`;

            item.append(num, conf);
            plateList.appendChild(item);
        });
        show(resultSection);
        resultSection.scrollIntoView({ behavior: 'smooth' });
    }

    async function loadHistory() {
        try {
            const res = await fetch('/api/history');
            const data = await res.json();
            historyBox.innerHTML = '';
            if (!data.history || data.history.length === 0) {
                historyBox.innerHTML = '<p class="empty">Chưa có lịch sử nhận diện.</p>';
                return;
            }
            data.history.forEach((h) => {
                const img = document.createElement('img');
                img.src = h.url;
                img.alt = h.filename;
                img.loading = 'lazy';
                historyBox.appendChild(img);
            });
        } catch (e) {
            historyBox.innerHTML = '<p class="empty">Không tải được lịch sử.</p>';
        }
    }

    loadHistory();
})();
