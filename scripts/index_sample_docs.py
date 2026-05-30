from pathlib import Path
from app.core.retriever import HybridRetriever

paths = list(Path('app/data/sample_docs').glob('*.txt')) + list(Path('app/data/sample_docs').glob('*.md'))
count = HybridRetriever().build_from_paths(paths)
print(f'Indexed {count} chunks from {len(paths)} sample files.')
