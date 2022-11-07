# 1st stage
FROM python:3.10.8-slim AS base
FROM base AS builder
COPY requirements.txt /requirements.txt
RUN pip install --user -r /requirements.txt
ENV PATH=/root/.local/bin:$PATH
RUN python -m spacy download en_core_web_md

# 2nd stage
FROM base

# copy only the dependencies installation from the 1st stage image
COPY --from=builder /root/.local /root/.local
COPY src /app
WORKDIR /app

# update PATH environment variable
ENV PATH=/home/app/.local/bin:$PATH

CMD ["python", "main.py"]