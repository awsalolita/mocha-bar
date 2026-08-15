"""
Amazon Polly unit functions — CLIENT only (no resource API).

client = boto3.client("polly")

Covers: text-to-speech (synthesize_speech -> audio stream), saving to file,
listing voices, and long-form async synthesis tasks that write to S3.
"""
import boto3


def get_client(region=None):
    return boto3.client("polly", region_name=region)


# ---- Synchronous synthesis ----
def polc_synthesize(client, text, voice_id="Joanna", output_format="mp3",
                    engine="neural", text_type="text"):
    """Returns the raw response; audio bytes via resp['AudioStream'].read().
    engine: 'standard' | 'neural' | 'long-form' | 'generative'.
    text_type: 'text' | 'ssml'."""
    return client.synthesize_speech(
        Text=text,
        VoiceId=voice_id,
        OutputFormat=output_format,
        Engine=engine,
        TextType=text_type)


def polc_synthesize_to_file(client, text, filename, voice_id="Joanna",
                            output_format="mp3", engine="neural"):
    """Synthesize and write the audio stream to a local file. Returns the path."""
    resp = client.synthesize_speech(
        Text=text, VoiceId=voice_id, OutputFormat=output_format, Engine=engine)
    with open(filename, "wb") as f:
        f.write(resp["AudioStream"].read())
    return filename


# ---- Voices ----
def polc_describe_voices(client, language_code=None, engine=None):
    """List available voices; optionally filter by language (e.g. 'en-US') / engine."""
    kwargs = {}
    if language_code:
        kwargs["LanguageCode"] = language_code
    if engine:
        kwargs["Engine"] = engine
    return client.describe_voices(**kwargs).get("Voices", [])


# ---- Async long-form synthesis (writes audio to S3) ----
def polc_start_speech_task(client, text, output_bucket, voice_id="Joanna",
                           output_format="mp3", engine="neural",
                           output_prefix=None, sns_topic_arn=None):
    """Start async synthesis task -> audio saved to S3. Returns the task dict."""
    kwargs = {
        "Text": text,
        "VoiceId": voice_id,
        "OutputFormat": output_format,
        "Engine": engine,
        "OutputS3BucketName": output_bucket,
    }
    if output_prefix:
        kwargs["OutputS3KeyPrefix"] = output_prefix
    if sns_topic_arn:
        kwargs["SnsTopicArn"] = sns_topic_arn
    return client.start_speech_synthesis_task(**kwargs)["SynthesisTask"]


def polc_get_speech_task(client, task_id):
    return client.get_speech_synthesis_task(TaskId=task_id)["SynthesisTask"]


def polc_list_speech_tasks(client, status=None):
    kwargs = {"Status": status} if status else {}
    return client.list_speech_synthesis_tasks(**kwargs).get("SynthesisTasks", [])
