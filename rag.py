"""
rag.py — RAG layer for Terraflow Studio.

Backends (auto-selected at runtime):
  ChromaDB + embeddings — when `chromadb` is installed AND EMBEDDING_PROVIDER is set
  BM25 (pure Python)    — fallback, no extra dependencies required

Embedding environment variables:
  EMBEDDING_PROVIDER   ollama | openai | gemini
  EMBEDDING_MODEL      nomic-embed-text | text-embedding-3-small | text-embedding-004
  EMBEDDING_BASE_URL   http://localhost:11434  (Ollama only, default shown)
  LLM_API_KEY          used for openai / gemini embeddings (same key as LLM)
"""
import json, math, re, os, pathlib, urllib.request
from collections import Counter

BASE_DIR    = pathlib.Path(__file__).parent
DOCS_DIR    = BASE_DIR / 'rag_docs'
INDEX_PATH  = pathlib.Path(os.environ.get('ODB_DATA_DIR', 'data')) / 'rag_index.json'
CHROMA_PATH = pathlib.Path(os.environ.get('ODB_DATA_DIR', 'data')) / 'chroma'

CHUNK_WORDS   = 350
OVERLAP_WORDS = 60
BM25_K1 = 1.5
BM25_B  = 0.75
COLLECTION    = 'odb_terraform'


# ── shared: chunking ──────────────────────────────────────────────────────────

def _tokenize(text):
    return re.findall(r'\b[a-z0-9_]+\b', text.lower())

def _chunk_file(path):
    words = path.read_text(encoding='utf-8').split()
    stem, chunks, i, seq = path.stem, [], 0, 0
    while i < len(words):
        chunks.append({
            'id':     f'{stem}_{seq}',
            'source': path.name,
            'text':   ' '.join(words[i : i + CHUNK_WORDS]),
        })
        seq += 1
        i   += CHUNK_WORDS - OVERLAP_WORDS
    return chunks

def _all_chunks():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    chunks = []
    for p in sorted(DOCS_DIR.glob('*.md')) + sorted(DOCS_DIR.glob('*.txt')):
        chunks.extend(_chunk_file(p))
    return chunks


# ── embedding ─────────────────────────────────────────────────────────────────

def _emb_provider():
    return os.environ.get('EMBEDDING_PROVIDER', '').lower().strip()

def _emb_model():
    defaults = {
        'ollama': 'nomic-embed-text',
        'openai': 'text-embedding-3-small',
        'gemini': 'text-embedding-004',
    }
    return os.environ.get('EMBEDDING_MODEL', defaults.get(_emb_provider(), ''))

def _embed_batch(texts):
    """Embed a list of strings. Returns list of float vectors."""
    provider = _emb_provider()

    if provider == 'ollama':
        base  = os.environ.get('EMBEDDING_BASE_URL', 'http://localhost:11434').rstrip('/')
        model = _emb_model()
        vecs  = []
        for text in texts:
            body = json.dumps({'model': model, 'input': text}).encode()
            req  = urllib.request.Request(
                f'{base}/api/embed', data=body,
                headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as r:
                vecs.append(json.loads(r.read())['embeddings'][0])
        return vecs

    if provider == 'openai':
        import openai
        client = openai.OpenAI(api_key=os.environ.get('LLM_API_KEY'))
        resp   = client.embeddings.create(model=_emb_model(), input=texts)
        return [d.embedding for d in resp.data]

    if provider == 'gemini':
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get('LLM_API_KEY'))
        m = f'models/{_emb_model()}'
        return [genai.embed_content(model=m, content=t)['embedding'] for t in texts]

    raise RuntimeError(f'Unknown EMBEDDING_PROVIDER: {provider!r}')

def _embed_one(text):
    return _embed_batch([text])[0]


# ── backend selector ──────────────────────────────────────────────────────────

def _use_chroma():
    """True when chromadb is importable AND an embedding provider is configured."""
    if not _emb_provider():
        return False
    try:
        import chromadb  # noqa: F401
        return True
    except ImportError:
        return False


# ── ChromaDB backend ──────────────────────────────────────────────────────────

_chroma_client = None

def _get_client():
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return _chroma_client

def _chroma_rebuild(chunks):
    client = _get_client()
    # get_or_create avoids a delete+create race in the Rust backend;
    # then we clear all existing documents before re-adding.
    col = client.get_or_create_collection(COLLECTION, metadata={'hnsw:space': 'cosine'})
    existing_ids = col.get(include=[])['ids']
    if existing_ids:
        col.delete(ids=existing_ids)
    if not chunks:
        return 0
    BATCH = 100
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i : i + BATCH]
        vecs  = _embed_batch([c['text'] for c in batch])
        col.add(
            ids        = [c['id']     for c in batch],
            documents  = [c['text']   for c in batch],
            embeddings = vecs,
            metadatas  = [{'source': c['source']} for c in batch],
        )
    return len(chunks)

def _chroma_retrieve(query, k):
    client = _get_client()
    try:
        col = client.get_collection(COLLECTION)
    except Exception:
        return []
    n = col.count()
    if n == 0:
        return []
    res = col.query(query_embeddings=[_embed_one(query)], n_results=min(k, n))
    return [
        {'id': doc_id, 'source': meta['source'], 'text': doc}
        for doc_id, doc, meta in zip(
            res['ids'][0], res['documents'][0], res['metadatas'][0]
        )
    ]

def _chroma_stats():
    client = _get_client()
    try:
        col    = client.get_collection(COLLECTION)
        n      = col.count()
        metas  = col.get(include=['metadatas'])['metadatas'] or []
        n_docs = len({m['source'] for m in metas})
    except Exception:
        n, n_docs = 0, 0
    return {
        'backend':    'chroma',
        'n_chunks':   n,
        'n_docs':     n_docs,
        'n_terms':    0,
        'index_path': str(CHROMA_PATH),
        'docs_dir':   str(DOCS_DIR),
    }


# ── BM25 backend ──────────────────────────────────────────────────────────────

_index_cache = None

def _invalidate_bm25():
    global _index_cache
    _index_cache = None

def _bm25_rebuild(chunks):
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not chunks:
        INDEX_PATH.write_text(json.dumps({'chunks': [], 'idf': {}, 'avg_len': 1, 'n_docs': 0}))
        _invalidate_bm25()
        return 0
    token_sets = []
    for c in chunks:
        toks        = _tokenize(c['text'])
        c['tf']     = dict(Counter(toks))
        c['length'] = len(toks)
        token_sets.append(set(toks))
    N       = len(chunks)
    idf     = {}
    for term in {t for ts in token_sets for t in ts}:
        df        = sum(1 for ts in token_sets if term in ts)
        idf[term] = math.log((N - df + 0.5) / (df + 0.5) + 1)
    avg_len = sum(c['length'] for c in chunks) / N
    INDEX_PATH.write_text(json.dumps(
        {'chunks': chunks, 'idf': idf, 'avg_len': avg_len, 'n_docs': N},
        indent=2,
    ))
    _invalidate_bm25()
    return N

def _load_bm25():
    global _index_cache
    if _index_cache is None:
        if not INDEX_PATH.exists():
            _bm25_rebuild(_all_chunks())
        _index_cache = json.loads(INDEX_PATH.read_text(encoding='utf-8'))
    return _index_cache

def _bm25_retrieve(query, k):
    idx    = _load_bm25()
    chunks = idx.get('chunks', [])
    if not chunks:
        return []
    idf     = idx.get('idf', {})
    avg_len = idx.get('avg_len', 1) or 1
    q_toks  = _tokenize(query)
    scores  = []
    for chunk in chunks:
        tf      = chunk.get('tf', {})
        doc_len = chunk.get('length', 1) or 1
        score   = sum(
            idf[t] * (tf.get(t, 0) * (BM25_K1 + 1)) /
            (tf.get(t, 0) + BM25_K1 * (1 - BM25_B + BM25_B * doc_len / avg_len))
            for t in q_toks if t in idf
        )
        scores.append((score, chunk))
    scores.sort(key=lambda x: x[0], reverse=True)
    return [c for s, c in scores[:k] if s > 0]

def _bm25_stats():
    idx = _load_bm25()
    return {
        'backend':    'bm25',
        'n_chunks':   len(idx.get('chunks', [])),
        'n_docs':     idx.get('n_docs', 0),
        'n_terms':    len(idx.get('idf', {})),
        'index_path': str(INDEX_PATH),
        'docs_dir':   str(DOCS_DIR),
    }


# ── public API ────────────────────────────────────────────────────────────────

def rebuild():
    """Index all docs in DOCS_DIR. Returns chunk count."""
    chunks = _all_chunks()
    if _use_chroma():
        return _chroma_rebuild(chunks)
    return _bm25_rebuild(chunks)

def retrieve(query, k=5):
    """Return top-k chunks by relevance for query."""
    if _use_chroma():
        return _chroma_retrieve(query, k)
    return _bm25_retrieve(query, k)

def build_context(query, k=5):
    """Return a formatted context block for LLM system prompt injection."""
    chunks = retrieve(query, k)
    if not chunks:
        return ''
    return '\n\n---\n\n'.join(f'[{c["source"]}]\n{c["text"]}' for c in chunks)

def index_stats():
    if _use_chroma():
        return _chroma_stats()
    return _bm25_stats()

def invalidate_cache():
    global _chroma_client
    _chroma_client = None
    _invalidate_bm25()
