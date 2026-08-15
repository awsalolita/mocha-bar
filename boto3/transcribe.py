"""
Amazon Transcribe unit functions — CLIENT only (no resource API).

client = boto3.client("transcribe")

Covers: async speech-to-text jobs (start/get/list/delete), waiting for
completion, and custom vocabularies. Audio must live in S3; the transcript
result is a JSON file Transcribe writes to S3 (URI in the job result).
"""
import time
import boto3


def get_client(region=None):
    return boto3.client("transcribe", region_name=region)


# ---- Transcription jobs ----
def trsc_start_job(client, job_name, media_s3_uri, media_format="mp3",
                   language="en-US", output_bucket=None):
    """Start async transcription. media_format: mp3|mp4|wav|flac|ogg|amr|webm."""
    kwargs = {
        "TranscriptionJobName": job_name,
        "Media": {"MediaFileUri": media_s3_uri},
        "MediaFormat": media_format,
        "LanguageCode": language,
    }
    if output_bucket:
        kwargs["OutputBucketName"] = output_bucket
    return client.start_transcription_job(**kwargs)


def trsc_start_job_auto_language(client, job_name, media_s3_uri, media_format="mp3"):
    """Let Transcribe auto-detect the language."""
    return client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": media_s3_uri},
        MediaFormat=media_format,
        IdentifyLanguage=True)


def trsc_get_job(client, job_name):
    return client.get_transcription_job(
        TranscriptionJobName=job_name)["TranscriptionJob"]


def trsc_list_jobs(client, status=None):
    """status: QUEUED | IN_PROGRESS | FAILED | COMPLETED (optional filter)."""
    kwargs = {"Status": status} if status else {}
    return client.list_transcription_jobs(**kwargs).get("TranscriptionJobSummaries", [])


def trsc_delete_job(client, job_name):
    return client.delete_transcription_job(TranscriptionJobName=job_name)


def trsc_wait_job(client, job_name, poll=10, timeout=600):
    """Poll until job COMPLETED/FAILED. Returns the job dict (check TranscriptFileUri)."""
    waited = 0
    while waited < timeout:
        job = client.get_transcription_job(
            TranscriptionJobName=job_name)["TranscriptionJob"]
        status = job["TranscriptionJobStatus"]
        if status in ("COMPLETED", "FAILED"):
            return job
        time.sleep(poll)
        waited += poll
    return job


# ---- Custom vocabulary ----
def trsc_create_vocabulary(client, name, phrases, language="en-US"):
    return client.create_vocabulary(
        VocabularyName=name, LanguageCode=language, Phrases=phrases)


def trsc_get_vocabulary(client, name):
    return client.get_vocabulary(VocabularyName=name)


def trsc_delete_vocabulary(client, name):
    return client.delete_vocabulary(VocabularyName=name)
