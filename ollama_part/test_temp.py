from services import ollama_services

service = ollama_services()
print(service.split_long_sentences_in_jsonl(
    "ollama_part/cache/harry-potter-and-the-philosophers-stone-by-jk-rowling/page_17.fixed.jsonl",
    min_length=80,
))
