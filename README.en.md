# Echo Player

AI-first language learning assistant focused on diagnosing and fixing listening/reading breakdowns across any language, with an end-to-end pipeline from raw text to targeted teaching.

## Why & Pain Points
- Learners know they are stuck but cannot locate whether the issue is at sound, word form, word meaning, syntax, or compositional semantics, so practice is inefficient.
- Long texts/audio are often split with duplication, omission, or reordering, breaking continuity.
- Typical tools only play audio or show captions and lack on-the-spot teaching plus traceable history.
- In multi-language scenarios, data prep, TTS, assessment, and logging are scattered and fail to form a closed loop.

## What It Does
- Diagnose issues across five processing layers, deliver targeted teaching, and keep a reviewable history.
- Full AI pipeline: PDF ingestion → sentence extraction → neural TTS → interactive UI → tutoring agent → learning log.
- Multi-language ready: OCR/LLM/TTS are not tied to English; plug different models per language.

## Full Flow (Five Parts)
1) **PDF → TextSegment (background agent)**  
   - Faithfully split multi-language PDFs into sequential `segment_id.txt` files; paragraph-first, ~300–800 words recommended; no skipping/rollback/duplication; only remove headers/footers/page numbers/OCR noise, no rewriting.
2) **TextSegment → CandidateSentence**  
   - Extract sentence-level learning units in original order; no rewriting/reordering/merging; keep context-dependent lines and short low-value snippets so users can skip quickly.
3) **CandidateSentence → TTS**  
   - Generate natural, emotionally varied speech per sentence; support multiple languages and speed control; return audio path and duration.
4) **UtteranceUnit (final output unit)**  
   - `unit_id`, `text`, `source_ref` (txt file or future timeline), `audio.path`, `audio.duration` for playback, shadowing, and comparison.
5) **Interactive Learning & Recording**  
   - UI shows text, recording/shadowing, five diagnostic buttons; sidebar offers layered diagnosis, explanations, examples, tests; log timeline and questions to build review plans.

## Five-Layer Diagnosis
1. Phonetic/Phonological: sound-to-phoneme, liaison/weak forms, word boundaries; misheard from sentence start.  
2. Lexical Form: choose the correct word form from sound; sound is right but word choice is wrong.  
3. Lexical Semantics: pick the right sense; unknown words or wrong sense of known words.  
4. Syntactic Parsing: subject-verb-object, modifiers, clauses/inversion/ellipsis; long sentences drift mid-way.  
5. Compositional Semantics: integrate word meanings and syntax into event meaning; every word is known but overall meaning fails.

## UI Highlights
- Top: latest three text segments for context.
- Bottom-left: recording/shadowing area with record, play recording, play original; can extend to auto pronunciation scoring.
- Bottom-right: five diagnostic buttons mapped to the five layers.
- Sidebar: layered explanations, examples, tests, and conversational teaching with live logging.

## AI-First & Extensible
- OCR/vision models to read PDFs (e.g., Qwen3-VL via ollama).
- Swappable multi-language TTS engines; future speaker/emotion control.
- Logs can feed LLMs to generate personalized review or retraining plans.
- `source_ref` can extend to video timelines (SRT) or other multimodal sources.

## Data Integrity Rules
- Strict order: `segment_id` increases without gaps, rollbacks, or duplication.
- No rewriting: only remove headers/footers/page numbers/OCR noise; never infer or add content.
- Context protection: process in batches and record progress; next run must continue from the last end point.

## Status
- In design/documentation phase; flow and interactions are defined. Next: finalize models, TTS choices, and UI prototype.
