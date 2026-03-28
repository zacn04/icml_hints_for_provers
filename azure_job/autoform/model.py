"""
Model wrapper stub.
Do NOT bake AzureML specifics here.
"""
from __future__ import annotations
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Model:
    provider: str
    name: str
    temperature: float
    max_tokens: int
    base_url: str = ""
    _tokenizer: Any = field(default=None, init=False, repr=False)
    _model: Any = field(default=None, init=False, repr=False)

    def generate(self, prompt: str, seed: int) -> str:
        if self.provider == "ollama":
            return self._generate_ollama(prompt, seed)
        elif self.provider == "hf":
            return self._generate_hf(prompt, seed)
        elif self.provider == "openai_compat":
            return self._generate_openai_compat(prompt, seed)
        else:
            return f"-- Error: unknown provider {self.provider}"
    
    def _generate_ollama(self, prompt: str, seed: int) -> str:
        # Ollama backend (local, HTTP API)
        # Note: Ollama API doesn't support seed, so we ignore it
        max_retries = 2
        timeout_sec = 60
        
        for attempt in range(max_retries):
            try:
                # Use curl to call Ollama API (simpler than Python HTTP client)
                request_data = {
                    "model": self.name,
                    "prompt": prompt,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                    }
                }
                
                cmd = [
                    "curl",
                    "-s",
                    "-X", "POST",
                    "http://localhost:11434/api/generate",
                    "-d", json.dumps(request_data),
                ]
                
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                )
                
                if proc.returncode == 0:
                    # Parse streaming response - collect all "response" fields
                    response_text = ""
                    for line in proc.stdout.strip().split("\n"):
                        if line:
                            try:
                                chunk = json.loads(line)
                                if "response" in chunk:
                                    response_text += chunk["response"]
                                if chunk.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
                    output = response_text.strip() if response_text else "-- Error: empty response"
                    return self._sanitize_output(output)
                else:
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                        continue
                    return f"-- Error: {proc.stderr[:200]}"
                    
            except subprocess.TimeoutExpired:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return "-- Error: timeout"
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return f"-- Error: {str(e)[:200]}"
        
        return "-- Error: max retries exceeded"
    
    def _generate_hf(self, prompt: str, seed: int) -> str:
        """HuggingFace Transformers backend."""
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM
        except ImportError:
            return "-- Error: transformers not installed"

        if self._tokenizer is None or self._model is None:
            try:
                self._tokenizer = AutoTokenizer.from_pretrained(self.name, trust_remote_code=True)

                use_cuda = torch.cuda.is_available()
                dtype = torch.float16 if use_cuda else torch.float32

                self._model = AutoModelForCausalLM.from_pretrained(
                    self.name,
                    device_map="auto" if use_cuda else None,
                    torch_dtype=dtype,
                    trust_remote_code=True
                )
                if not use_cuda:
                    self._model = self._model.to("cpu")

                # Ensure pad token exists
                if self._tokenizer.pad_token_id is None and self._tokenizer.eos_token_id is not None:
                    self._tokenizer.pad_token = self._tokenizer.eos_token

            except Exception as e:
                return f"-- Error: failed to load model: {str(e)[:200]}"

        # IMPORTANT: DeepSeek-Prover wants raw Lean completion prompt.
        # Do NOT wrap in English instruction text. Do NOT use chat template.
        completion_prompt = prompt
        if not completion_prompt.endswith("\n"):
            completion_prompt += "\n"

        inputs = self._tokenizer(completion_prompt, return_tensors="pt")

        device = next(self._model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

        do_sample = self.temperature > 0.0
        generate_kwargs = {
            "max_new_tokens": self.max_tokens,
            "do_sample": do_sample,
            "pad_token_id": self._tokenizer.pad_token_id,
        }
        if self._tokenizer.eos_token_id is not None:
            generate_kwargs["eos_token_id"] = self._tokenizer.eos_token_id

        if do_sample:
            generate_kwargs["temperature"] = float(self.temperature)
            generate_kwargs["top_p"] = 0.95

        with torch.no_grad():
            outputs = self._model.generate(**inputs, **generate_kwargs)

        input_length = inputs["input_ids"].shape[1]
        generated_ids = outputs[0][input_length:]
        output_text = self._tokenizer.decode(generated_ids, skip_special_tokens=True)

        return self._sanitize_output(output_text)

    def _generate_openai_compat(self, prompt: str, seed: int) -> str:
        """OpenAI-compatible API backend (vLLM, Together, Fireworks, etc)."""
        import urllib.request
        import urllib.error

        url = self.base_url or os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
        url = url.rstrip("/")
        endpoint = f"{url}/completions"

        api_key = os.environ.get("OPENAI_API_KEY", "EMPTY")

        request_data = json.dumps({
            "model": self.name,
            "prompt": prompt,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": 0.95,
            "seed": seed,
        }).encode("utf-8")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(
                    endpoint,
                    data=request_data,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    text = result["choices"][0]["text"]
                    return self._sanitize_output(text)
            except urllib.error.HTTPError as e:
                if e.code == 429 or e.code >= 500:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                return f"-- Error: HTTP {e.code}: {e.reason}"
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return f"-- Error: {str(e)[:200]}"

        return "-- Error: max retries exceeded"

    def _sanitize_output(self, text: str) -> str:
        t = text.strip()

        # If ANY fence marker appears anywhere, truncate at the first occurrence.
        # This handles the common "dangling closing ```" case.
        if "```" in t:
            t = t.split("```", 1)[0].rstrip()

        # Also drop any remaining stray fence lines
        lines = []
        for line in t.splitlines():
            if line.strip().startswith("```"):
                break
            lines.append(line)
        t = "\n".join(lines).strip()

        # Your existing guards:
        if t.lstrip().startswith(("theorem ", "import ")):
            return "sorry"
        if t.startswith("by "):
            t = t[3:].strip()
        if t.startswith("by\n"):
            t = t[3:].strip()
        return t if t else "sorry"