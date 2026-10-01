# Data

- `tasks/benign_tasks.json`: the normal tasks used to measure usefulness, each with automatic checks.
- `attacks/`: injection scenarios. The file format is in `attacks/README.md`.
- `benign/`: benign tool outputs, including hard negatives such as instructional text that is not addressed to the agent.

Large or generated files belong in `data/generated/`, which is ignored by Git. Record every source, license, and generation step in the dataset datasheet.
