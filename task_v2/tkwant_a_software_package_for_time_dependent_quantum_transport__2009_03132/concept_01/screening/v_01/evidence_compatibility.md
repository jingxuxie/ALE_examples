# Grader-only compatibility repair

The public contract allows additional diagnostic columns and experiments and does not limit claim references to exactly three table filenames. The fresh participant produced additional checks/comparison/qualification tables. The original grader's claim lookup would reject those references before even checking their arithmetic.

The grader now loads additional submission-local CSV files with unique row IDs. It rejects traversal and external symlinks. This changes no task text, input, hidden case, target trace, numerical tolerance, core-scoring function, runtime limit, memory limit, or classification threshold. The original evaluator is preserved as `evaluate_original.py`. Both versions give identical reference evidence credit because the reference uses only the original tables.

This is not a task redesign and is not evidence of participant difficulty. The fresh session receives no feedback, extra data, or new instructions. Numerical hardness is judged solely by the frozen core score; additional evidence is also reviewed against the retained raw experiments. No scientific scoring has been tuned in response to an agent outcome.
