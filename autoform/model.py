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

    def generate_chat(self, messages: list, seed: int) -> str:
        """Chat completions for models that require chat format (V2, Kimina)."""
        if self.provider == "openai_compat":
            return self._generate_openai_chat_compat(messages, seed)
        elif self.provider == "hf":
            # For HF, apply chat template and generate as completion
            return self._generate_hf_chat(messages, seed)
        else:
            return f"-- Error: chat mode not supported for provider {self.provider}"
    
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

    def _generate_openai_chat_compat(self, messages: list, seed: int) -> str:
        """OpenAI-compatible chat completions endpoint (vLLM, etc)."""
        import urllib.request
        import urllib.error

        url = self.base_url or os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
        url = url.rstrip("/")
        endpoint = f"{url}/chat/completions"

        api_key = os.environ.get("OPENAI_API_KEY", "EMPTY")

        request_data = json.dumps({
            "model": self.name,
            "messages": messages,
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
                    text = result["choices"][0]["message"]["content"]
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

    def _generate_hf_chat(self, messages: list, seed: int) -> str:
        """HF backend for chat models — apply chat template then generate."""
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
                    self.name, device_map="auto" if use_cuda else None,
                    torch_dtype=dtype, trust_remote_code=True,
                )
                if not use_cuda:
                    self._model = self._model.to("cpu")
                if self._tokenizer.pad_token_id is None and self._tokenizer.eos_token_id is not None:
                    self._tokenizer.pad_token = self._tokenizer.eos_token
            except Exception as e:
                return f"-- Error: failed to load model: {str(e)[:200]}"

        prompt = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self._tokenizer(prompt, return_tensors="pt")
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
        if do_sample:
            generate_kwargs["temperature"] = float(self.temperature)
            generate_kwargs["top_p"] = 0.95

        with torch.no_grad():
            outputs = self._model.generate(**inputs, **generate_kwargs)

        input_length = inputs["input_ids"].shape[1]
        generated_ids = outputs[0][input_length:]
        output_text = self._tokenizer.decode(generated_ids, skip_special_tokens=True)
        return self._sanitize_output(output_text)

    def _sanitize_output(self, text: str) -> str:
        import re, sys, os
        _dbg = os.environ.get("SANITIZE_DEBUG") == "1"
        if _dbg:
            print(f"[SANDBG] enter: text len={len(text)}, first 60: {text[:60]!r}", file=sys.stderr, flush=True)
        t = text.strip()
        if _dbg:
            print(f"[SANDBG] stripped: t len={len(t)}, first 60: {t[:60]!r}", file=sys.stderr, flush=True)

        # Reasoning-mode output (V2/Kimina): the model produces prose + one or
        # more ```lean4 ... ``` code blocks. Extract the LAST such block.
        code_blocks = re.findall(r"```(?:lean4?|lean)\s*\n(.*?)```", t, re.DOTALL)
        if _dbg:
            print(f"[SANDBG] code_blocks count: {len(code_blocks)}", file=sys.stderr, flush=True)
        if code_blocks:
            body = code_blocks[-1].strip()
            if _dbg:
                print(f"[SANDBG] block body first 80: {body[:80]!r}", file=sys.stderr, flush=True)
            # Some reasoning models (Kimina) emit a whole-file block:
            # `import Mathlib`, `open ...`, then a fresh theorem signature
            # with the proof. Strip leading import/open lines before the
            # theorem-signature walk so we don't echo them inside the outer
            # `by` block (which Lean rejects as `unexpected token 'import'`).
            while True:
                m_io = re.match(r"\s*(import|open)\s+[^\n]*\n?", body)
                if not m_io:
                    break
                body = body[m_io.end():]
            body = body.lstrip()
            if _dbg:
                print(f"[SANDBG] post-import-strip body first 80: {body[:80]!r}", file=sys.stderr, flush=True)
            # If the block opens with a theorem/lemma/example signature,
            # strip off the signature up to and including the FIRST `:= by`
            # at bracket depth 0. (The signature may span multiple lines
            # because of binders like `(a : ℝ)` and hypotheses; `.rfind`
            # would wrongly match nested `have h : ... := by tac` inside
            # the body.)
            opener = re.match(r"\s*(theorem|lemma|example)\b", body)
            if opener:
                depth = 0
                i = opener.start()
                n = len(body)
                while i < n - 4:
                    c = body[i]
                    if c in "([{":
                        depth += 1
                    elif c in ")]}":
                        depth -= 1
                    elif depth == 0 and body.startswith(":= by", i):
                        body = body[i + len(":= by"):].lstrip("\n")
                        break
                    i += 1
            if body.startswith("by "):
                body = body[3:].strip()
            elif body.startswith("by\n"):
                body = body[3:].strip()
            # Normalize indentation: Lean requires the body to be indented
            # relative to `:= by`. V2/Kimina typically emit the body at
            # column 0 after signature stripping, which Lean rejects.
            lines = body.rstrip().split("\n")
            # Find minimum indent across non-blank lines
            non_blank_lines = [l for l in lines if l.strip()]
            if non_blank_lines:
                min_indent = min(
                    len(l) - len(l.lstrip()) for l in non_blank_lines
                )
                # First, dedent so the outermost line starts at column 0
                if min_indent > 0:
                    lines = [l[min_indent:] if l.strip() else l for l in lines]
                # Then re-indent everything by 2 spaces so the body sits
                # inside the `by` block of the theorem signature.
                lines = ["  " + l if l.strip() else l for l in lines]
                body = "\n".join(lines)
            return body if body.strip() else "sorry"

        # No fenced code block found. Reasoning models like Kimina sometimes
        # emit a full Lean file (import + open + nested theorem signature +
        # proof body) without markdown fences. Detect that pattern and
        # extract the inner by-block before falling back to the completion-
        # mode logic.
        stripped = t.lstrip()
        if _dbg:
            print(f"[SANDBG] no fences. stripped first 60: {stripped[:60]!r}", file=sys.stderr, flush=True)
            print(f"[SANDBG] starts_with_import={stripped.startswith('import ')}, starts_with_open={stripped.startswith('open ')}", file=sys.stderr, flush=True)
        if stripped.startswith("import ") or stripped.startswith("open "):
            # Drop leading import/open lines.
            inner = t
            while True:
                m = re.match(r"\s*(import|open)\s+[^\n]*\n?", inner)
                if not m:
                    break
                inner = inner[m.end():]
            inner = inner.lstrip()
            if _dbg:
                print(f"[SANDBG] post-strip inner first 80: {inner[:80]!r}", file=sys.stderr, flush=True)
            # If what remains begins with a theorem/lemma/example signature,
            # walk to its `:= by` at bracket depth 0 and take the body.
            if re.match(r"(theorem|lemma|example)\b", inner):
                if _dbg:
                    print(f"[SANDBG] theorem matched, walking to := by", file=sys.stderr, flush=True)
                depth = 0
                i = 0
                n = len(inner)
                while i < n - 4:
                    c = inner[i]
                    if c in "([{":
                        depth += 1
                    elif c in ")]}":
                        depth -= 1
                    elif depth == 0 and inner.startswith(":= by", i):
                        if _dbg:
                            print(f"[SANDBG] found := by at i={i}, depth=0, extracting", file=sys.stderr, flush=True)
                        body = inner[i + len(":= by"):].lstrip("\n")
                        # Re-indent to sit inside the outer `by` block.
                        lines = body.rstrip().split("\n")
                        non_blank = [l for l in lines if l.strip()]
                        if non_blank:
                            min_indent = min(len(l) - len(l.lstrip()) for l in non_blank)
                            if min_indent > 0:
                                lines = [l[min_indent:] if l.strip() else l for l in lines]
                            lines = ["  " + l if l.strip() else l for l in lines]
                            body = "\n".join(lines)
                        return body if body.strip() else "sorry"
                    i += 1
            # Couldn't recover a body; fall through to "sorry" guard below.

        # Completion-mode fallback (Goedel, V1.5): truncate at the first
        # fence so dangling closers don't leak explanatory prose into the
        # proof.
        # However, if the response contains markdown reasoning markers
        # (###, **bold**, bullet lists) without a usable ```lean4 block,
        # it's a failed reasoning-model output — don't try to treat the
        # prose as tactics.
        if re.search(r"(^|\n)#{2,}\s", t) or "**" in t:
            return "sorry"
        if "```" in t:
            t = t.split("```", 1)[0].rstrip()
        lines = []
        for line in t.splitlines():
            if line.strip().startswith("```"):
                break
            lines.append(line)
        t = "\n".join(lines).strip()

        if t.lstrip().startswith(("theorem ", "import ")):
            return "sorry"
        if t.startswith("by "):
            t = t[3:].strip()
        if t.startswith("by\n"):
            t = t[3:].strip()
        return t if t else "sorry"