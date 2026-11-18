# Dragon Medical One

Dragon Medical One has no API, so these transcripts are shipped rather than
produced by `make evaluate`. Each utterance was dictated by hand in the desktop
client and the raw output kept as-is. As for every other system, no keyterm
biasing, context prompt or term list was used.

## Version

```
2026.1 (26.1.60348.0)
```

## Client settings

| Setting | Value |
|---|---|
| Mikrofon | Nuance PowerMic Mobile |
| Sprache | Deutsch (Schweiz) |
| Fachgebiet | Medizin - allgemein |

## Source

Each raw `.txt` output was matched to its dataset row by file basename
(`audio.path`). The result is the same `{"id", "hypothesis"}` JSONL as the
other systems.
