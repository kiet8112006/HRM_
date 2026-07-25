# 1. Dùng Slim Image chính thức
FROM python:3.10-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Biến môi trường
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 2. Cài đặt ODBC Driver cho SQL Server (Debian 12)
# Cài đặt ODBC Driver 17 & 18 cho SQL Server (Debian 12)
RUN apt-get update && apt-get install -y --no-install-requests \
    curl \
    gnupg2 \
    unixodbc-dev \
    ca-certificates \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*
# 3. CACHE LAYER: Copy requirements.txt và cài thư viện TRƯỚC
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy toàn bộ source code
COPY . .

# 🔒 BẢO MẬT: Tạo user mới "appuser" và chuyển quyền hạn khỏi root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Lệnh khởi chạy app
CMD ["python", "app.py"]