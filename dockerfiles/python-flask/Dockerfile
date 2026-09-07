FROM public.ecr.aws/docker/library/python:3.14-slim as build

WORKDIR /app
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt


FROM public.ecr.aws/docker/library/python:3.14-slim as runtime

ARG user=1000
ARG group=1000

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ngrep \
    && rm -rf /var/lib/apt/lists/*

USER $user:$group
WORKDIR /app

COPY --from=build /install /usr/local
COPY src src

ENTRYPOINT ["python3", "src/app.py"]
