# Architecture Notes

## Retrieval design

The retriever combines semantic vectors and BM25. This matters for scientific PDFs because semantic similarity is useful for concepts, while BM25 is useful for exact terms such as dataset names, acronyms, variables, equations, and method names.

## Grounding design

The answer generator receives only retrieved evidence. It is instructed to cite source and page. If `OPENAI_API_KEY` is missing, the system uses extractive evidence mode instead of failing.

## Production upgrade path

For production, replace local JSON/pickle/NumPy storage with Postgres + Qdrant, add document permissions, OCR, table parsing, audit logging, and a formal evaluation pipeline.
