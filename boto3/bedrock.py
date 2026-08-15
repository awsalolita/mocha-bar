"""
Amazon Bedrock unit functions — CLIENT only (no resource API).

Two DIFFERENT clients:
  control = boto3.client("bedrock")           -> manage models/guardrails/jobs
  runtime = boto3.client("bedrock-runtime")   -> actually call the models

Covers: list foundation models, InvokeModel (raw), Converse (unified chat),
streaming, embeddings, and the model-specific request bodies (Anthropic Claude,
Amazon Titan/Nova, Meta Llama).
"""
import json
import boto3


def get_client(region=None):
    """Control-plane: list/manage models, guardrails, model-invocation jobs."""
    return boto3.client("bedrock", region_name=region)


def get_runtime_client(region=None):
    """Data-plane: invoke_model / converse etc. This is what you call to run inference."""
    return boto3.client("bedrock-runtime", region_name=region)


# ============================================================
# ------------------- CONTROL PLANE --------------------------
# ============================================================

def brc_list_foundation_models(client, by_provider=None):
    """List available foundation models. by_provider e.g. 'Anthropic', 'Amazon', 'Meta'."""
    kwargs = {"byProvider": by_provider} if by_provider else {}
    return client.list_foundation_models(**kwargs).get("modelSummaries", [])


def brc_get_foundation_model(client, model_id):
    return client.get_foundation_model(modelIdentifier=model_id)["modelDetails"]


def brc_list_custom_models(client):
    return client.list_custom_models().get("modelSummaries", [])


# ---- Guardrails ----
def brc_create_guardrail(client, name, blocked_input_msg="Blocked.",
                         blocked_output_msg="Blocked."):
    return client.create_guardrail(
        name=name,
        blockedInputMessaging=blocked_input_msg,
        blockedOutputsMessaging=blocked_output_msg)


def brc_list_guardrails(client):
    return client.list_guardrails().get("guardrails", [])


# ============================================================
# ------------------- RUNTIME (INVOKE) -----------------------
# ============================================================

def brrt_invoke_model(runtime, model_id, body, accept="application/json",
                      content_type="application/json"):
    """Low-level invoke. `body` is a dict (model-specific) — JSON-encoded here.
    Returns the parsed JSON response body."""
    resp = runtime.invoke_model(
        modelId=model_id,
        body=json.dumps(body),
        accept=accept,
        contentType=content_type)
    return json.loads(resp["body"].read())


def brrt_invoke_model_stream(runtime, model_id, body):
    """Streaming invoke. Yields each parsed chunk dict as it arrives."""
    resp = runtime.invoke_model_with_response_stream(
        modelId=model_id, body=json.dumps(body))
    for event in resp["body"]:
        chunk = event.get("chunk")
        if chunk:
            yield json.loads(chunk["bytes"])


# ---- Converse API (unified messages format across all providers) ----
def brrt_converse(runtime, model_id, messages, system=None,
                  max_tokens=512, temperature=0.7):
    """Unified chat call. messages = [{"role":"user","content":[{"text":"hi"}]}].
    Returns the assistant text."""
    kwargs = {
        "modelId": model_id,
        "messages": messages,
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
    }
    if system:
        kwargs["system"] = [{"text": system}]
    resp = runtime.converse(**kwargs)
    return resp["output"]["message"]["content"][0]["text"]


def brrt_converse_stream(runtime, model_id, messages, system=None,
                         max_tokens=512, temperature=0.7):
    """Streaming Converse. Yields incremental text deltas."""
    kwargs = {
        "modelId": model_id,
        "messages": messages,
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
    }
    if system:
        kwargs["system"] = [{"text": system}]
    resp = runtime.converse_stream(**kwargs)
    for event in resp["stream"]:
        delta = event.get("contentBlockDelta", {}).get("delta", {})
        if "text" in delta:
            yield delta["text"]


# ============================================================
# ---- Provider-specific request-body builders (for invoke) --
# ============================================================

def brrt_claude(runtime, prompt, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
                max_tokens=512, system=None, temperature=0.7):
    """Anthropic Claude via the Messages API body. Returns text."""
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
    }
    if system:
        body["system"] = system
    out = brrt_invoke_model(runtime, model_id, body)
    return out["content"][0]["text"]


def brrt_titan_text(runtime, prompt, model_id="amazon.titan-text-express-v1",
                    max_tokens=512, temperature=0.7):
    """Amazon Titan Text. Returns generated text."""
    body = {
        "inputText": prompt,
        "textGenerationConfig": {"maxTokenCount": max_tokens,
                                 "temperature": temperature},
    }
    out = brrt_invoke_model(runtime, model_id, body)
    return out["results"][0]["outputText"]


def brrt_llama(runtime, prompt, model_id="meta.llama3-8b-instruct-v1:0",
               max_gen_len=512, temperature=0.7):
    """Meta Llama. Returns generated text."""
    body = {"prompt": prompt, "max_gen_len": max_gen_len, "temperature": temperature}
    out = brrt_invoke_model(runtime, model_id, body)
    return out["generation"]


# ---- Embeddings ----
def brrt_titan_embedding(runtime, text, model_id="amazon.titan-embed-text-v2:0"):
    """Return the embedding vector (list[float]) for a piece of text."""
    out = brrt_invoke_model(runtime, model_id, {"inputText": text})
    return out["embedding"]


# ---- Image generation (Titan Image / Nova Canvas returns base64 PNG) ----
def brrt_titan_image(runtime, prompt, model_id="amazon.titan-image-generator-v1",
                     num_images=1, width=1024, height=1024):
    """Returns list of base64-encoded PNG strings."""
    body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {"text": prompt},
        "imageGenerationConfig": {"numberOfImages": num_images,
                                  "width": width, "height": height},
    }
    out = brrt_invoke_model(runtime, model_id, body)
    return out["images"]
