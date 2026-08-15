"""
Amazon Comprehend unit functions — CLIENT only (no resource API).

client = boto3.client("comprehend")

Covers: language detection, sentiment, entities, key phrases, PII, syntax —
both single-document (sync) and batch (up to 25 docs) variants.

Most calls need a LanguageCode (e.g. 'en'). detect_dominant_language does not.
"""
import time
import boto3


def get_client(region=None):
    return boto3.client("comprehend", region_name=region)


# ---- Single document ----
def cmpc_detect_dominant_language(client, text):
    """Returns list of {'LanguageCode', 'Score'} sorted by score."""
    return client.detect_dominant_language(Text=text).get("Languages", [])


def cmpc_detect_sentiment(client, text, language="en"):
    """Returns dict with 'Sentiment' (POSITIVE/NEGATIVE/NEUTRAL/MIXED) + scores."""
    return client.detect_sentiment(Text=text, LanguageCode=language)


def cmpc_sentiment_label(client, text, language="en"):
    """Convenience: return just the sentiment label string
    (POSITIVE/NEGATIVE/NEUTRAL/MIXED)."""
    return client.detect_sentiment(
        Text=text, LanguageCode=language)["Sentiment"]


def cmpc_sentiment_score(client, text, language="en"):
    """Convenience: return (label, confidence_float) for the winning sentiment."""
    resp = client.detect_sentiment(Text=text, LanguageCode=language)
    label = resp["Sentiment"]
    confidence = resp["SentimentScore"][label.capitalize()]
    return label, confidence


def cmpc_detect_entities(client, text, language="en"):
    """Named entities (people, places, dates, quantities...)."""
    return client.detect_entities(Text=text, LanguageCode=language).get("Entities", [])


def cmpc_detect_key_phrases(client, text, language="en"):
    return client.detect_key_phrases(
        Text=text, LanguageCode=language).get("KeyPhrases", [])


def cmpc_detect_pii(client, text, language="en"):
    """Detect PII spans (offsets + type, e.g. EMAIL, SSN)."""
    return client.detect_pii_entities(
        Text=text, LanguageCode=language).get("Entities", [])


def cmpc_detect_syntax(client, text, language="en"):
    """Tokens + part-of-speech tags."""
    return client.detect_syntax(
        Text=text, LanguageCode=language).get("SyntaxTokens", [])


def cmpc_detect_targeted_sentiment(client, text, language="en"):
    """Entity-level (targeted) sentiment."""
    return client.detect_targeted_sentiment(
        Text=text, LanguageCode=language).get("Entities", [])


# ---- Batch (up to 25 documents per call) ----
def cmpc_batch_detect_sentiment(client, text_list, language="en"):
    return client.batch_detect_sentiment(
        TextList=text_list, LanguageCode=language)


def cmpc_batch_sentiment_labels(client, text_list, language="en"):
    """Convenience: return a list of sentiment labels aligned to text_list order."""
    resp = client.batch_detect_sentiment(TextList=text_list, LanguageCode=language)
    labels = [None] * len(text_list)
    for r in resp.get("ResultList", []):
        labels[r["Index"]] = r["Sentiment"]
    return labels


def cmpc_batch_detect_entities(client, text_list, language="en"):
    return client.batch_detect_entities(
        TextList=text_list, LanguageCode=language)


def cmpc_batch_detect_key_phrases(client, text_list, language="en"):
    return client.batch_detect_key_phrases(
        TextList=text_list, LanguageCode=language)


# ---- Async analysis jobs (large corpora in S3) ----
def cmpc_start_sentiment_job(client, input_s3_uri, output_s3_uri, role_arn,
                             language="en", job_name=None):
    """Start an async sentiment-detection job over documents in S3."""
    kwargs = {
        "InputDataConfig": {"S3Uri": input_s3_uri, "InputFormat": "ONE_DOC_PER_LINE"},
        "OutputDataConfig": {"S3Uri": output_s3_uri},
        "DataAccessRoleArn": role_arn,
        "LanguageCode": language,
    }
    if job_name:
        kwargs["JobName"] = job_name
    return client.start_sentiment_detection_job(**kwargs)


def cmpc_describe_sentiment_job(client, job_id):
    return client.describe_sentiment_detection_job(
        JobId=job_id)["SentimentDetectionJobProperties"]


def cmpc_list_sentiment_jobs(client, status=None):
    """status filter: SUBMITTED | IN_PROGRESS | COMPLETED | FAILED | STOPPED."""
    kwargs = {"Filter": {"JobStatus": status}} if status else {}
    return client.list_sentiment_detection_jobs(
        **kwargs).get("SentimentDetectionJobPropertiesList", [])


def cmpc_stop_sentiment_job(client, job_id):
    return client.stop_sentiment_detection_job(JobId=job_id)


def cmpc_wait_sentiment_job(client, job_id, poll=15, timeout=900):
    """Poll until the async sentiment job COMPLETED/FAILED/STOPPED.
    Returns the job properties (check OutputDataConfig.S3Uri for the result file)."""
    waited = 0
    while waited < timeout:
        props = client.describe_sentiment_detection_job(
            JobId=job_id)["SentimentDetectionJobProperties"]
        if props["JobStatus"] in ("COMPLETED", "FAILED", "STOPPED"):
            return props
        time.sleep(poll)
        waited += poll
    return props
