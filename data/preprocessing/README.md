# Preprocessing artifacts

This directory contains only repository-authored synthetic fixtures. No restricted manuscript data is stored here.

## W9 RIME Cat.1883 + Cat.2095 photo geometry diagnostic

`w9_rime_cat1883_cat2095_geometry.json` pins the RIME Fig. 6 recto TIFF by exact URL, 36,023,444-byte length, dimensions and SHA-256. The source file and every derivative remain in the user's private W9 vault outside Git. The optional `inspect-rime-image` CLI verifies the acquisition packet and exact bytes, decodes one bounded TIFF frame, applies metadata orientation, and writes a deterministic PNG showing only the outer non-white photographed-content bounds. The rectangle includes the scale target; it is not a papyrus mask, region segmentation, column/line annotation, OCR, or gold.

Example (local private paths are intentionally not recorded in project evidence):

```powershell
python -m tools.preprocessing inspect-rime-image --image <private-vault>/CAT1883-CAT2095-RIME-fig6-recto-original.tif --evidence <private-vault>/CAT1883-CAT2095-FIG6.json --output <new-private-vault-child>
```

The processed image comes from a RIME figure scan with publication processing, not a claimed first-generation museum master. CC BY 2.0 applies to the figure image on the evidence available; reuse rights for Landrino's article transcription are not verified. Article line counts and citations may guide future human examination, but this path deliberately creates no line identity or text-to-image alignment. The source remains unregistered, benchmark-quarantined, blocked for training/development, and unauthorized for evaluation.
