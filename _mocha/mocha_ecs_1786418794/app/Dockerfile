FROM public.ecr.aws/docker/library/alpine:3.20

RUN apk add --no-cache curl ngrep

ARG user=1000
ARG group=1000

USER $user:$group
WORKDIR /app

COPY --chown=$user:$group plant config.ini .

RUN chmod +x plant

ENTRYPOINT ["/app/plant"]
