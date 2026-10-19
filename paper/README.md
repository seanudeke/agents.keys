# Manuscript source

`agents_with_keys_submission.md` is current. The original draft and v2 are retained for history; superseded counts are not pooled. `figure1.py` and `figure1.svg` distinguish the implemented validator from proposed services.

```bash
python -m pip install -r paper/requirements.txt
python paper/build_manuscript.py --artifact-commit "$(git rev-parse HEAD)" --output /tmp/awkeys-manuscript
cd /tmp/awkeys-manuscript
pdflatex -interaction=nonstopmode -halt-on-error manuscript.tex
pdflatex -interaction=nonstopmode -halt-on-error manuscript.tex
```

Outputs include an editable Word manuscript, LaTeX source, IEEE PDF, and vector/raster Figure 1. A TeX distribution is required. Unmodified IEEEtran.cls 1.8b comes from CTAN; SHA-256: `da751920a317ed318b7b5cd7fa585a6cc7d28502d457856382e9be24b10a3bd7`.

Supply the external artifact commit only after committing the regenerated inventory. AGENT 2027 uses the IEEE conference template, eight pages including references, and single-anonymous review. The author and IEEE-required generated-content acknowledgment are retained.
