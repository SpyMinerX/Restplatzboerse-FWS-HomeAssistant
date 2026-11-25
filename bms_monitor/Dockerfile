FROM mcr.microsoft.com/playwright/python:v1.51.1-noble
RUN pip install --no-cache-dir playwright==1.51.1 requests openpyxl xlrd defusedxml
COPY monitor.py /monitor.py
CMD ["python", "-u", "/monitor.py"]
