# The money-shot demo, runnable by a stranger with zero Python setup:
#   docker build -t parley . && docker run --rm -p 8080:8080 parley
# then open http://127.0.0.1:8080 and press Run.
#
# The parley/ core is zero-dependency stdlib, so this image needs no pip install and no build step.
FROM python:3.12-slim

WORKDIR /app
COPY parley/ ./parley/
COPY examples/ ./examples/

# Bind to all interfaces so the container is reachable from the host.
# PYTHONPATH=/app makes the zero-dependency `parley` package importable when the
# demo is launched as a script (`python examples/demo/server.py`) with no pip install.
ENV PARLEY_HOST=0.0.0.0 \
    PARLEY_PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app
EXPOSE 8080

CMD ["python", "examples/demo/server.py"]
