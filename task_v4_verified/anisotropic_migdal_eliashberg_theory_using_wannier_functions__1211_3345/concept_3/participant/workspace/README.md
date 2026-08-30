# Submission workspace

Put `solve.py` and any fitted assets here. The entry point accepts
`--input FILE --output FILE`. Only public resources may be used.
The evaluator exposes the candidate and public resources read-only and gives
the subprocess fresh scratch containing only public test features. Public
resources are found through `ALE_PUBLIC_INPUT`. Use only one Python process.
