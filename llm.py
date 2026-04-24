"""
llm.py — Model-agnostic LLM provider layer for Terraflow Studio.
Supported: anthropic, openai (+ compatible), gemini, ollama
Set LLM_PROVIDER, LLM_API_KEY, LLM_MODEL, LLM_BASE_URL in .env
"""
import json, os, urllib.request, urllib.error
from typing import Optional

_DEFAULTS = {
    'anthropic': 'claude-3-5-haiku-20241022',
    'openai':    'gpt-4o-mini',
    'gemini':    'gemini-1.5-flash',
    'ollama':    'llama3.2',
}

def _post(url, payload, headers, timeout=60):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data,
           headers={'Content-Type':'application/json', **headers}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'HTTP {e.code}: {body[:400]}')
    except urllib.error.URLError as e:
        raise RuntimeError(f'Network error: {e.reason}')

class AnthropicProvider:
    URL = 'https://api.anthropic.com/v1/messages'
    def __init__(self, key, model):
        if not key: raise RuntimeError('LLM_API_KEY is required for anthropic.')
        self.key = key; self.model = model or _DEFAULTS['anthropic']
        self.max_tokens = int(os.environ.get('LLM_MAX_TOKENS','2048'))
        self.timeout    = int(os.environ.get('LLM_TIMEOUT','60'))
    def chat(self, messages):
        system = ''; filtered = []
        for m in messages:
            if m['role'] == 'system': system = m['content']
            else: filtered.append(m)
        payload = {'model':self.model,'max_tokens':self.max_tokens,'messages':filtered}
        if system: payload['system'] = system
        r = _post(self.URL, payload, {'x-api-key':self.key,'anthropic-version':'2023-06-01'}, self.timeout)
        return r['content'][0]['text']
    @property
    def info(self): return {'provider':'anthropic','model':self.model}

class OpenAIProvider:
    DEFAULT = 'https://api.openai.com/v1/chat/completions'
    def __init__(self, key, model, base_url=''):
        if not key: raise RuntimeError('LLM_API_KEY is required for openai.')
        self.key = key; self.model = model or _DEFAULTS['openai']
        self.temperature = float(os.environ.get('LLM_TEMPERATURE','0.2'))
        self.max_tokens  = int(os.environ.get('LLM_MAX_TOKENS','2048'))
        self.timeout     = int(os.environ.get('LLM_TIMEOUT','60'))
        url = (base_url or self.DEFAULT).rstrip('/')
        self.url = url if url.endswith('/chat/completions') else url + '/chat/completions'
    def chat(self, messages):
        r = _post(self.url, {'model':self.model,'messages':messages,
            'max_tokens':self.max_tokens,'temperature':self.temperature},
            {'Authorization':f'Bearer {self.key}'}, self.timeout)
        return r['choices'][0]['message']['content']
    @property
    def info(self): return {'provider':'openai','model':self.model,'base_url':self.url}

class GeminiProvider:
    BASE = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
    def __init__(self, key, model, base_url=''):
        if not key: raise RuntimeError('LLM_API_KEY is required for gemini.')
        self.key = key; self.model = model or _DEFAULTS['gemini']
        self.base_url    = base_url.rstrip('/') if base_url else ''
        self.max_tokens  = int(os.environ.get('LLM_MAX_TOKENS','2048'))
        self.temperature = float(os.environ.get('LLM_TEMPERATURE','0.2'))
        self.timeout     = int(os.environ.get('LLM_TIMEOUT','60'))
    def _endpoint(self):
        if self.base_url:
            tmpl = self.base_url + ('/{model}:generateContent' if '{model}' not in self.base_url else '')
            return tmpl.format(model=self.model)
        return self.BASE.format(model=self.model) + f'?key={self.key}'
    def chat(self, messages):
        contents = []; system_parts = []
        for m in messages:
            if m['role'] == 'system': system_parts.append({'text':m['content']})
            elif m['role'] == 'user': contents.append({'role':'user','parts':[{'text':m['content']}]})
            else:                     contents.append({'role':'model','parts':[{'text':m['content']}]})
        payload = {'contents':contents,'generationConfig':{'maxOutputTokens':self.max_tokens,'temperature':self.temperature}}
        if system_parts: payload['systemInstruction'] = {'parts':system_parts}
        headers = {}
        if self.base_url:
            bearer = os.environ.get('LLM_BEARER_TOKEN','').strip()
            if bearer: headers['Authorization'] = f'Bearer {bearer}'
        r = _post(self._endpoint(), payload, headers, self.timeout)
        return r['candidates'][0]['content']['parts'][0]['text']
    @property
    def info(self):
        i = {'provider':'gemini','model':self.model}
        if self.base_url: i['base_url'] = self.base_url
        return i

class OllamaProvider:
    DEFAULT = 'http://localhost:11434/api/chat'
    def __init__(self, model, base_url=''):
        self.model    = model or _DEFAULTS['ollama']
        self.url      = base_url or self.DEFAULT
        self.temperature = float(os.environ.get('LLM_TEMPERATURE','0.2'))
        self.timeout     = int(os.environ.get('LLM_TIMEOUT','60'))
    def chat(self, messages):
        r = _post(self.url, {'model':self.model,'messages':messages,'stream':False,
            'options':{'temperature':self.temperature}}, {}, self.timeout)
        return r['message']['content']
    @property
    def info(self): return {'provider':'ollama','model':self.model,'base_url':self.url}

def _make_provider():
    p       = os.environ.get('LLM_PROVIDER','anthropic').lower()
    key     = os.environ.get('LLM_API_KEY','').strip()
    model   = os.environ.get('LLM_MODEL','').strip()
    base_url= os.environ.get('LLM_BASE_URL','').strip()
    if p == 'anthropic': return AnthropicProvider(key, model)
    if p == 'openai':    return OpenAIProvider(key, model, base_url)
    if p == 'gemini':    return GeminiProvider(key, model, base_url)
    if p == 'ollama':    return OllamaProvider(model, base_url)
    raise RuntimeError(f"Unknown LLM_PROVIDER '{p}'. Use: anthropic, openai, gemini, ollama")

_provider = None; _provider_error = None

def _get_provider():
    global _provider, _provider_error
    if _provider is None and _provider_error is None:
        try: _provider = _make_provider()
        except Exception as e: _provider_error = str(e)
    if _provider_error: raise RuntimeError(_provider_error)
    return _provider

def chat(messages): return _get_provider().chat(messages)

def provider_info():
    p   = os.environ.get('LLM_PROVIDER','anthropic').lower()
    key = os.environ.get('LLM_API_KEY','').strip()
    model = os.environ.get('LLM_MODEL','').strip() or _DEFAULTS.get(p,'')
    base_url = os.environ.get('LLM_BASE_URL','').strip()
    configured = p == 'ollama' or bool(key)
    if not configured:
        return {'configured':False,'provider':p,'error':f'LLM_API_KEY is not set in .env'}
    return {'configured':True,'provider':p,'model':model,'base_url':base_url or None}
