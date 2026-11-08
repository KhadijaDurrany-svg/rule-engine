FROM python:3.12-slim

# Non-root user
RUN useradd --create-home --uid 10001 kiln
WORKDIR /app

# Install the package first (layer-cached) then copy sources.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

USER kiln

# Default: run the offline benchmark, printing results without writing files.
ENTRYPOINT ["rulekiln"]
CMD ["bench", "--no-write"]
