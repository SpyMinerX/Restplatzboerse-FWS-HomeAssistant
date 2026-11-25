FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN pip install --no-cache-dir playwright==1.51.0 requests openpyxl xlrd defusedxml
RUN python -m playwright install --with-deps chromium
COPY monitor.py /monitor.py
CMD ["python", "-u", "/monitor.py"]
