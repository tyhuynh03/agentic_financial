# DJIA Stock Analysis Agent

Ứng dụng phân tích dữ liệu chứng khoán DJIA (Dow Jones Industrial Average) sử dụng SQL Agent và Streamlit.

## Yêu cầu hệ thống

- Python 3.8 trở lên
- Docker
- PostgreSQL với pgvector extension

## Cài đặt

1. Clone repository:
```bash
git clone <repository_url>
cd agno
```

2. Tạo và kích hoạt môi trường ảo:
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

3. Cài đặt các thư viện phụ thuộc:
```bash
pip install -r requirements.txt
```

4. Khởi động PostgreSQL container:
```bash
# Tạo volume để lưu trữ dữ liệu
docker volume create pgvolume

# Khởi động container
docker run -d \
  --name pgvector \
  -e POSTGRES_DB=ai \
  -e POSTGRES_USER=ai \
  -e POSTGRES_PASSWORD=ai \
  -e PGDATA=/var/lib/postgresql/data/pgdata \
  -v pgvolume:/var/lib/postgresql/data \
  -p 5532:5432 \
  agnohq/pgvector:16
```

5. Kiểm tra container đã chạy:
```bash
docker ps
```

6. Xem log của container:
```bash
docker logs pgvector
```

## Cấu hình

1. Tạo file `.env` với nội dung:
```env
OPENAI_API_KEY=<your_openai_api_key>
GOOGLE_API_KEY=<your_google_api_key>
GROQ_API_KEY=<your_groq_api_key>
DATABASE_URL=postgresql://ai:ai@localhost:5532/ai
```

2. Hoặc cập nhật biến môi trường trực tiếp:
```bash
# Windows
set DATABASE_URL=postgresql://ai:ai@localhost:5532/ai
# Linux/Mac
export DATABASE_URL=postgresql://ai:ai@localhost:5532/ai
```

3. Cập nhật file `config.py` nếu cần thiết.

## Chạy ứng dụng

1. Load dữ liệu vào database:
```bash
python cookbook/examples/apps/sql_agent/load_data.py
```

2. Load knowledge base:
```bash
python cookbook/examples/apps/sql_agent/load_knowledge.py
```

3. Khởi động Streamlit app:
```bash
streamlit run cookbook/examples/apps/sql_agent/app.py
```

4. Truy cập ứng dụng tại http://localhost:8501

## Sử dụng

Ứng dụng cung cấp các chức năng:

1. Phân tích dữ liệu chứng khoán DJIA:
   - So sánh hiệu suất giữa các ngành
   - Xem thông tin chi tiết từng công ty
   - Phân tích giá và khối lượng giao dịch

2. Các câu truy vấn mẫu:
   - Show Tables - Xem danh sách bảng
   - Top Market Cap - Top 5 công ty theo vốn hóa
   - Sector Performance - So sánh hiệu suất ngành
   - Trading Volume - Khối lượng giao dịch Apple
   - Dividend Yield - Công ty có cổ tức cao nhất
   - Price Range - Biến động giá 52 tuần
   - Moving Average - Trung bình động 30 ngày

3. Tùy chọn model:
   - llama-4-scout
   - gemini-2.5-pro-exp-03-25

## Cấu trúc thư mục

```
cookbook/examples/apps/sql_agent/
├── app.py              # Streamlit application
├── load_data.py        # Script để load dữ liệu
├── load_knowledge.py   # Script để load knowledge base
├── utils.py           # Utility functions
├── data/              # Thư mục chứa dữ liệu
└── knowledge/         # Thư mục chứa knowledge base
```

## Lưu ý

1. Đảm bảo PostgreSQL container đang chạy trước khi khởi động ứng dụng:
```bash
# Kiểm tra trạng thái
docker ps

# Nếu container đã dừng, khởi động lại
docker start pgvector

# Nếu cần xóa và tạo lại container
docker rm -f pgvector
docker volume rm pgvolume
```

2. Kiểm tra các API key trong file `.env` đã được cấu hình đúng
3. Nếu sử dụng Gemini model, lưu ý giới hạn 5 request/phút
4. Sử dụng dấu ngoặc kép cho tên cột trong câu truy vấn SQL (ví dụ: `"Ticker"`, `"Close"`)
5. Dữ liệu được lưu trong Docker volume `pgvolume`, sẽ không bị mất khi restart container
6. Port mặc định của PostgreSQL là 5532, có thể thay đổi trong lệnh `docker run` nếu cần 