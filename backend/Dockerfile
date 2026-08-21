FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 可通过 build arg 指定 pip 镜像源（国内网络建议用清华/阿里云镜像）
ARG PIP_INDEX_URL=https://pypi.org/simple

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i ${PIP_INDEX_URL}

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
