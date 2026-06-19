"""Download embedding model from ModelScope (China-accessible)."""
from modelscope import snapshot_download

model_dir = snapshot_download(
    'iic/nlp_corom_sentence-embedding_english-base',
    cache_dir='D:/BIGONE/data/model_cache',
)
print(f"Model downloaded to: {model_dir}")
