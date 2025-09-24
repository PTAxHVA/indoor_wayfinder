# Indoor Wayfinder

Hệ thống tìm đường trong nhà sử dụng FastAPI và NetworkX, hỗ trợ tìm đường thông minh dựa trên ngôn ngữ tự nhiên tiếng Việt.

Lấy cảm hứng từ repo https://github.com/KnotzerIO/indoor-wayfinder

## 🚀 Tính năng chính

- **Tìm đường thông minh**: Hỗ trợ tìm đường bằng câu hỏi tự nhiên tiếng Việt (ví dụ: "từ tòa A đến phòng B202")
- **Quản lý bản đồ**: Upload và quản lý nhiều bản đồ tầng khác nhau
- **Editor trực quan**: Giao diện web để vẽ nodes và edges trên bản đồ
- **Tìm kiếm fuzzy**: Tìm kiếm địa điểm thông minh với khả năng gợi ý khi không tìm thấy
- **Hướng dẫn chi tiết**: Tạo hướng dẫn đi đường từng bước với góc quay và khoảng cách
- **Multi-floor support**: Hỗ trợ nhiều tầng và tìm đường giữa các tầng

## 🏗️ Kiến trúc hệ thống

### Backend (FastAPI)
- **API RESTful** với FastAPI
- **Database**: SQLite với SQLModel ORM
- **Graph processing**: NetworkX cho thuật toán tìm đường
- **NLP**: Xử lý ngôn ngữ tự nhiên tiếng Việt
- **Fuzzy search**: Tìm kiếm mờ với RapidFuzz

### Frontend (Vanilla JS)
- **User Interface**: Giao diện người dùng để tìm đường
- **Editor Interface**: Giao diện chỉnh sửa bản đồ
- **Interactive Map**: Tương tác với bản đồ và hiển thị đường đi

## 📁 Cấu trúc thư mục

```
indoor_wayfinder/
├── backend/                 # Backend FastAPI
│   ├── core/               # Cấu hình cơ sở dữ liệu
│   ├── models/             # SQLModel entities
│   ├── routers/            # API endpoints
│   │   ├── admin.py        # Quản trị hệ thống
│   │   ├── aliases.py      # Quản lý tên địa điểm
│   │   ├── edges.py        # Quản lý đường đi
│   │   ├── maps.py         # Quản lý bản đồ
│   │   ├── nodes.py        # Quản lý điểm nút
│   │   └── routes.py       # API tìm đường
│   ├── services/           # Business logic
│   └── utils/              # Utilities (NLP, geometry, normalization)
├── frontend/               # Frontend web
│   ├── user.html          # Giao diện người dùng
│   ├── editor.html        # Giao diện chỉnh sửa
│   ├── user.js            # Logic người dùng
│   ├── editor.js          # Logic chỉnh sửa
│   └── app.css            # Stylesheet
├── data/                  # Dữ liệu
│   ├── db/                # SQLite database
│   └── uploads/           # Hình ảnh bản đồ
└── requirements.txt       # Python dependencies
```

## 🛠️ Cài đặt và chạy

### Yêu cầu hệ thống
- Python 3.8+

### Cài đặt

1. **Clone repository**
```bash
git clone https://github.com/LTB122/indoor_wayfinder.git
cd indoor_wayfinder
```

2. **Cài đặt dependencies**
```bash
pip install -r requirements.txt
```

3. **Chạy server**
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

5. **Truy cập ứng dụng**
- **User Interface**: (Vẫn đang phát triển)
- **Editor Interface**: http://localhost:8000/app/editor.html
- **API Documentation**: http://localhost:8000/docs

## 📖 Hướng dẫn sử dụng

### 1. Quản lý bản đồ (Editor)

1. Truy cập **Editor Interface**
2. **Upload bản đồ mới**:
   - Nhập tên bản đồ
   - Chọn tầng
   - Nhập tỷ lệ pixels/meter
   - Upload file ảnh
3. **Thêm điểm nút (Nodes)**:
   - Click "**+ Thêm điểm**"
   - Click trên bản đồ để đặt vị trí
   - Nhập tên địa điểm (alias)
4. **Vẽ đường đi (Edges)**:
   - Click "**⟂ Vẽ đường**"
   - Click vào node đầu tiên
   - Click các điểm trung gian
   - Double-click vào node đích để kết thúc

### 2. Tìm đường (User)

1. Truy cập **User Interface**
2. **Chọn bản đồ** từ dropdown
3. **Nhập câu hỏi** tự nhiên:
   - "từ tòa A đến phòng B202"
   - "đi đến thư viện"
   - "từ vị trí hiện tại đến canteen"
4. **Đặt vị trí hiện tại** (tùy chọn)
5. **Click "Tìm đường"** để xem hướng dẫn

## 🔧 API Endpoints

### Maps
- `GET /maps` - Lấy danh sách bản đồ
- `POST /maps` - Tạo bản đồ mới
- `GET /maps/{map_id}` - Lấy thông tin bản đồ

### Nodes
- `GET /nodes` - Lấy danh sách nodes
- `POST /nodes` - Tạo node mới
- `PUT /nodes/{node_id}` - Cập nhật node

### Routes
- `POST /route` - Tìm đường đi
- `POST /route/suggest` - Gợi ý địa điểm

### Admin
- `POST /admin/clear-map` - Xóa dữ liệu bản đồ
- `GET /admin/stats` - Thống kê hệ thống

## 🧠 Thuật toán tìm đường

1. **NLP Processing**: Phân tích câu hỏi để trích xuất điểm đầu và cuối
2. **Fuzzy Matching**: Tìm kiếm địa điểm gần đúng nhất
3. **Graph Building**: Xây dựng đồ thị từ nodes và edges
4. **Path Finding**: Sử dụng Dijkstra algorithm để tìm đường ngắn nhất
5. **Instruction Generation**: Tạo hướng dẫn chi tiết với góc quay và khoảng cách

## 🎯 Tính năng nâng cao

- **Multi-language support**: Hỗ trợ tiếng Việt và tiếng Anh
- **Fuzzy search**: Tìm kiếm thông minh với gợi ý
- **Real-time editing**: Chỉnh sửa bản đồ trực tuyến
- **Responsive design**: Giao diện thân thiện trên mọi thiết bị
- **CORS enabled**: Hỗ trợ tích hợp với frontend khác

## 🔍 Troubleshooting

### Lỗi thường gặp

1. **"Map không tồn tại"**: Kiểm tra map_id có đúng không
2. **"Không tìm thấy đường đi"**: Kiểm tra nodes và edges đã được tạo chưa
3. **"Không load được ảnh"**: Kiểm tra file ảnh trong thư mục `data/uploads/`

### Debug

- Kiểm tra logs trong terminal
- Sử dụng API docs tại `/docs` để test endpoints
- Kiểm tra database tại `data/db/wayfinder.db`

## 📝 License

MIT License - Xem file LICENSE để biết thêm chi tiết.

## 🤝 Contributing

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## 📞 Support

Nếu gặp vấn đề, vui lòng tạo issue trên GitHub repository.
