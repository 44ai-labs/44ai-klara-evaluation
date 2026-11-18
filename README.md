# Klara Evaluation

Scoring Code | Normalization Rules | All Transcripts

📝 [Klara: Medical Speech Recognition for Real-World Clinical Environments](https://44ai.ch/klara/paper.pdf)  
🤗 [44ai-clinical-de](https://huggingface.co/datasets/44ai/44ai-clinical-de-validation)  
🗣️ [Release Blogpost](https://44ai.ch/klara/)

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/44ai-labs/44ai-klara-evaluation
cd 44ai-klara-evaluation
cp .env.example .env
# the test set is gated: request access, then set HF_TOKEN in .env
make install
make score
```

`make score` reads the transcripts in `transcriptions/`, so it needs no vendor account and no API key.

## Results

Accuracy in %, as 100 minus the error rate. Higher is better.

| System | Formatted | Medical terms | Word Accuracy |
|---|---:|---:|---:|
| **Klara** | **90.9** | **90.4** | **92.7** |
| Corti Symphony | 80.1 | 89.6 | 87.0 |
| ElevenLabs Scribe v2 Medical | 76.7 | 89.0 | 88.3 |
| gpt-4o-transcribe | 74.9 | 88.5 | 88.6 |
| Dragon Medical One | 72.2\* | 76.7\* | 75.6 |
| ElevenLabs Scribe v2 | 72.1 | 87.8 | 87.3 |
| Nemotron 3.5 Transcribe | 69.6 | 81.5 | 84.1 |
| MAI-Transcribe-2 | 66.0 | 84.6 | 88.3 |
| Cohere Transcribe | 55.8\* | 78.1\* | 79.6 |
| Soniox stt-async-v5 | 53.8 | 83.6 | 84.8 |
| Whisper large-v3 | 53.3\* | 78.3\* | 78.1 |
| Deepgram Nova-3 | 42.6 | 73.3 | 75.1 |

*Formatted* and *Medical terms* cover all three test sets, weighted by audio duration. *Word Accuracy* is
on 44ai-clinical-de. \* The system received MedTerm and MedDictate as clips of at most 30 s.

Per-set numbers, including the sets on which other systems lead, are in `results/result_<timestamp>.md`.

## Metrics

| Metric | Definition | Compared texts |
|---|---|---|
| Word accuracy | 100 − WER | output and reference, both normalized |
| Medical term accuracy | 100 − MER, the share of the reference's medical terms that are missing | output and reference, both normalized, with each test set's own term list |
| Formatted accuracy | 100 − fWER | raw output and formatted reference: case, punctuation, numbers and line breaks count |

- Each system is scored in one configuration. Where a system can deliver formatted text, that run is
  used for every metric.
- On 44ai-clinical-de, every system's WER is scored against the spoken-form reference, the only form
  in which that set has a term list. On MedTerm and MedDictate, runs that deliver formatted text are
  scored against the formatted reference, and Soniox stt-async-v5, Deepgram Nova-3, Whisper large-v3
  and Cohere Transcribe against the spoken-form reference.
- Formatted text comes from a built-in step (Klara, Dragon Medical One), a vendor option (Corti
  Symphony's spoken and automatic punctuation, MAI-Transcribe-2's clean style, Deepgram's smart format)
  or one shared instruction (ElevenLabs Scribe v2 and Scribe v2 Medical, gpt-4o-transcribe,
  Nemotron 3.5 Transcribe). The
  instruction is in `src/klara_benchmark/systems/formatting.py` and is the same for every system.
- The plain runs of these systems are kept. `make score` writes every run of every system to
  `results/tab_configurations.tex`, with how it treats dictated commands and numbers.
- A medical term that is split into, or glued to, other words still counts as recognized.
- No system gets keyterm biasing or the medical-term list. The shared instruction is the only prompt,
  apart from the plain Nemotron run, which gets its model card's transcription prompt.

## Test sets

| Name | Content | Source |
|---|---|---|
| `44ai-clinical-val` | 44ai-clinical-de: 4'331 clinical dictations, 12 h, nine dialects and accents | [44ai/44ai-clinical-de-validation](https://huggingface.co/datasets/44ai/44ai-clinical-de-validation) |
| `medterm` | German portion of Corti MedTerm: 200 recordings, 4.1 h | [corti/med-term](https://huggingface.co/datasets/corti/med-term) |
| `meddictate` | German portion of Corti MedDictate: 9 recordings, 0.5 h | [corti/med-dictate](https://huggingface.co/datasets/corti/med-dictate) |

The 44ai datasets are gated: request access on their pages and set `HF_TOKEN` in `.env`. Both Corti sets
are pinned to a revision in `src/klara_benchmark/datasets.py`.

Systems that only take short audio get the Corti sets as clips of at most 30 s:
[44ai-corti-med-term-de-chunked](https://huggingface.co/datasets/44ai/44ai-corti-med-term-de-chunked) and
[44ai-corti-med-dictate-de-chunked](https://huggingface.co/datasets/44ai/44ai-corti-med-dictate-de-chunked).
Their clip transcripts are joined per recording and scored against the same references as everyone else.

## Systems

| Name | Backend | Needs |
|---|---|---|
| `klara` | 44ai API | `KLARA_API_URL`, `KLARA_API_KEY` (contact frederic.odermatt@44ai.ch for access) |
| `elevenlabs` | ElevenLabs Scribe v2 API | `ELEVENLABS_API_KEY` |
| `elevenlabs-formatted` | ElevenLabs Scribe v2 API with the shared formatting instruction | as `elevenlabs` |
| `elevenlabs-medical` | ElevenLabs Scribe v2 Medical API | as `elevenlabs` |
| `elevenlabs-medical-formatted` | ElevenLabs Scribe v2 Medical API with the shared formatting instruction | as `elevenlabs` |
| `gpt-4o` | OpenAI gpt-4o-transcribe API | `OPENAI_API_KEY` |
| `gpt-4o-formatted` | OpenAI gpt-4o-transcribe API with the shared formatting instruction as prompt | as `gpt-4o` |
| `deepgram` | Deepgram Nova-3 API | `DEEPGRAM_API_KEY` |
| `soniox` | Soniox stt-async-v5 API | `SONIOX_API_KEY` |
| `mai-transcribe` | Microsoft MAI-Transcribe-2 (Azure Speech), verbatim style | `MAI_TRANSCRIBE_ENDPOINT`, `MAI_TRANSCRIBE_API_KEY` |
| `mai-transcribe-formatted` | Microsoft MAI-Transcribe-2 (Azure Speech), clean style | as `mai-transcribe` |
| `corti` | Corti Symphony API, as dictated | `CORTI_CLIENT_ID`, `CORTI_CLIENT_SECRET`, `CORTI_TENANT_NAME` |
| `corti-formatted` | Corti Symphony API, spoken and automatic punctuation | as `corti` |
| `whisper` | openai/whisper-large-v3, local, clips | `make install-local` |
| `cohere` | CohereLabs/cohere-transcribe-03-2026, local, clips | `make install-local` |
| `nemotron` | nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B on a local vLLM server, the model card's prompt | `NEMOTRON_API_URL`, `make install-local` |
| `nemotron-formatted` | the same server with the shared formatting instruction as prompt | as `nemotron` |
| `dmo` | Nuance Dragon Medical One, desktop app, clips | dictated by hand, see [`transcriptions/dmo/README.md`](transcriptions/dmo/README.md) |

## Run a system yourself

```sh
make evaluate klara elevenlabs   # -> transcriptions/<system>/<set>.jsonl
make score
```

`whisper` and `cohere` run locally (GPU recommended) after `make install-local`. `nemotron` needs
that too, and a vLLM server running the model as its
[model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B) describes.

ElevenLabs returns slightly different transcripts from run to run even with the fixed seed, so a
re-run will not reproduce its stored transcripts word for word. The same holds for Nemotron, whose
output depends on which requests the server batches together. The numbers above come from the
frozen transcripts.

## Normalization

`normalize()` applies these steps in order, identically to reference, hypothesis and term list, and returns
every intermediate stage. WER and MER are computed after it. fWER is computed on the raw texts.

1. NFC, lowercase, line breaks -> punctuation mark
2. symbols -> words (`%` -> "prozent", `°C` -> "grad celsius", `≥` -> "größer gleich")
3. German number words -> digits ("drei" -> "3", ordinals, decimals, number words glued into compounds),
   the German thousands dot ("18.200" ≡ "18200") and spelled-out ranges ("3 bis 5" ≡ "3-5")
4. dates and times -> one digit form ("15. April 2024" ≡ "15.04.2024")
5. unit words -> abbreviations ("milligramm" -> "mg", "Millimeter Quecksilbersäule" -> "mmHg"),
   including the spoken divider ("pro Minute" ≡ "/min")
6. joined, hyphenated and split spellings of listed terms -> one form
7. curated Latinate spelling variants ("Carcinom" -> "Karzinom", "Ulcus" -> "Ulkus")
8. clinical abbreviations -> spelled-out phrase ("Z.n." ≡ "Zustand nach")
9. spoken punctuation and glyphs -> one shared mark
10. umlaut and eszett folding ("ä" -> "ae", "ß" -> "ss")

There is no blanket character rewriting: a misheard "Torax" for "Thorax" stays an error.

WER and fWER glue a letter hyphen ("Butterfly-Plastik" -> "butterflyplastik"). MER splits it
(`split_compounds=True`), because it matches terms per word span.

## Use the metrics as a library

The metric core is installable on its own, pinned by commit:

```sh
pip install "44ai-klara-evaluation @ git+https://github.com/44ai-labs/44ai-klara-evaluation@<sha>"
```

```python
from klara_evaluation import fwer_counts, mer_counts, normalize, wer_counts

terms = ["Ramipril", "Thorax"]
spoken = "Ramipril fünf Milligramm Komma Zustand nach Röntgen Thorax Punkt"
written = "Ramipril 5 mg, Z.n. Röntgen Thorax."
misheard = "Ramipril 5 mg, Z.n. Röntgen Torax."

# WER: (edits, reference words) on the normalized pair.
ref = normalize(spoken, terms).final
wer_counts(ref, normalize(written, terms).final)   # (0, 9)
wer_counts(ref, normalize(misheard, terms).final)  # (1, 9)

# MER: (missing terms, reference terms). It matches terms per word span, hence split_compounds.
ref = normalize(spoken, terms, split_compounds=True).final
hyp = normalize(misheard, terms, split_compounds=True).final
mer_counts(ref, hyp, [normalize(t, terms, split_compounds=True).final for t in terms])  # (1, 2)

# fWER: the raw pair. Case, punctuation and line breaks count.
fwer_counts(written, spoken)  # (6, 8)
```

## Repository

```
src/klara_evaluation/   metric library: normalization, WER, fWER, MER
src/klara_benchmark/    harness: datasets, one module per system, evaluate, score, paper tables
transcriptions/         the stored output of every system on every test set
```

## References

- German orthography rule authority: [RfdR Amtliches Regelwerk §32](https://www.rechtschreibrat.com/DOX/RfdR_Amtliches-Regelwerk_2024.pdf)
- Over-normalization caveat: [arXiv:2409.02449](https://arxiv.org/pdf/2409.02449)

## License

Code is MIT. The datasets carry their own licenses, see the dataset cards.
