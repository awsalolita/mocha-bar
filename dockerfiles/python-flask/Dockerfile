FROM public.ecr.aws/docker/library/python:3.14-slim as build

WORKDIR /app

COPY requirements.txt .

# Install into an isolated prefix so the runtime stage can copy just the
# packages (no pip/build artifacts). --prefix keeps the standard
# lib/pythonX.Y/site-packages layout so it drops straight into /usr/local.
RUN pip install --prefix=/install -r requirements.txt

# ---

FROM public.ecr.aws/docker/library/python:3.14-slim as runtime

ARG user=1000
ARG group=1000

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ngrep \
    && rm -rf /var/lib/apt/lists/*

USER $user:$group
WORKDIR /app

# Land deps in the interpreter's default site-packages (/usr/local/...), so
# they're on sys.path without PYTHONPATH. The CloudWatch/OTel operator can then
# set PYTHONPATH freely for auto-instrumentation without hiding Flask.
COPY --from=build /install /usr/local
COPY src src

ENTRYPOINT ["python3", "src/app.py"]
