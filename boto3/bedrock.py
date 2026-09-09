"""
Amazon Bedrock unit functions — CLIENT only (no resource API).

Three DIFFERENT clients:
  control   = boto3.client("bedrock")               -> manage models, custom models, provisioned throughput, guardrails
  runtime   = boto3.client("bedrock-runtime")       -> run inference (InvokeModel, Converse) on models or deployed ARNs
  agent_rt  = boto3.client("bedrock-agent-runtime") -> invoke deployed Bedrock Agents & Knowledge Bases

Covers: list foundation/custom/provisioned models, InvokeModel (raw), Converse (unified chat),
quick prompt, streaming, embeddings, images, and Bedrock Agents.
"""
import json
import boto3


def get_client(region=None):
    """Control-plane: list/manage models, guardrails, provisioned throughput."""
    return boto3.client("bedrock", region_name=region)


def get_runtime_client(region=None):
    """Data-plane: invoke_model / converse. Runs inference on foundation model IDs or deployed model ARNs."""
    return boto3.client("bedrock-runtime", region_name=region)


def get_agent_runtime_client(region=None):
    """Agent data-plane: invoke Bedrock Agents or query Knowledge Bases."""
    return boto3.client("bedrock-agent-runtime", region_name=region)


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


def brc_list_provisioned_model_throughputs(client):
    """List deployed provisioned model throughputs and their ARNs."""
    return client.list_provisioned_model_throughputs().get("provisionedModelSummaries", [])


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


def brrt_quick_prompt(runtime, prompt, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
                      system=None, max_tokens=512, temperature=0.7):
    """Fastest single-turn call for contests.
    `model_id` can be:
      - Foundation Model ID: e.g. 'anthropic.claude-3-5-sonnet-20240620-v1:0'
      - Cross-region inference profile ID: e.g. 'us.anthropic.claude-3-5-sonnet-20240620-v1:0'
      - Deployed / Provisioned Model ARN: e.g. 'arn:aws:bedrock:...'
    Returns the assistant's text response string."""
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    return brrt_converse(runtime, model_id, messages, system=system,
                         max_tokens=max_tokens, temperature=temperature)


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


# ============================================================
# ------------- BEDROCK AGENT RUNTIME ------------------------
# ============================================================

def brart_invoke_agent(agent_rt, agent_id, agent_alias_id, session_id, prompt):
    """Invoke a deployed Bedrock Agent. Returns the full text response from stream."""
    resp = agent_rt.invoke_agent(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId=session_id,
        inputText=prompt,
    )
    chunks = []
    for event in resp.get("completion", []):
        chunk = event.get("chunk")
        if chunk and "bytes" in chunk:
            chunks.append(chunk["bytes"].decode("utf-8"))
    return "".join(chunks)


def brart_retrieve_and_generate(agent_rt, kb_id, prompt, model_arn=None):
    """Query a Bedrock Knowledge Base and generate an answer.
    Default model is Claude 3.5 Sonnet if model_arn is not provided."""
    m_arn = model_arn or "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"
    kwargs = {
        "input": {"text": prompt},
        "retrieveAndGenerateConfiguration": {
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": kb_id,
                "modelArn": m_arn,
            },
        },
    }
    resp = agent_rt.retrieve_and_generate(**kwargs)
    return resp["output"]["text"]


# ============================================================
# ------------- SAGEMAKER RUNTIME (IF DEPLOYED ENDPOINT) -----
# ============================================================

def get_sagemaker_runtime_client(region=None):
    """Client for invoking deployed Amazon SageMaker model endpoints."""
    return boto3.client("sagemaker-runtime", region_name=region)


def sm_invoke_endpoint(sm_runtime, endpoint_name, payload, content_type="application/json"):
    """Invoke an Amazon SageMaker real-time endpoint. `payload` can be a dict or str.
    Returns parsed JSON response (or string if not JSON)."""
    body_data = json.dumps(payload) if isinstance(payload, (dict, list)) else payload
    resp = sm_runtime.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType=content_type,
        Body=body_data,
    )
    raw = resp["Body"].read().decode("utf-8")
    try:
        return json.loads(raw)
    except Exception:
        return raw

