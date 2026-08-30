# Paid Off Clothes. The whole app is Python standard library, so there is no pip install step and
# nothing to pin — the image is the interpreter plus about 5MB of site.
FROM python:3.12-slim

# Unbuffered so logs appear immediately in `fly logs`; no .pyc clutter in the image.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POC_DATA_DIR=/data \
    PORT=8080

WORKDIR /app

# Run as a non-root user. If the app is ever compromised it should not own the filesystem.
RUN useradd --create-home --shell /usr/sbin/nologin poc \
    && mkdir -p /data \
    && chown -R poc:poc /data

COPY --chown=poc:poc . /app

# Anything writable belongs on the mounted volume, never in the image. These are copied in as a
# seed on first boot by bootstrap(); leaving the originals here is what makes that possible.
USER poc

EXPOSE 8080

# The host restarts the machine if this stops answering, so it has to touch the database rather
# than just prove the process exists.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4).status==200 else 1)"

CMD ["python3", "server.py"]
