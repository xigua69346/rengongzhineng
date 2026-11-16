# S2 source and evidence backup

User-selected public backup of source, tests, frozen model parameters, reports, sanitized real API evidence and complete historical SHA256 inventories. Raw experimental trajectories, virtual environments, node_modules, credentials and private session/run mappings remain on the original local workspace. This is version rollback within the preserved local project, not a full standalone data disaster-recovery archive. Restore the original protected data before inference; no retraining or recalibration is authorized.

The original workspace had no .git metadata. This independent snapshot repository does not invent prior Git history and will not replace the remote main branch. Stage only the reviewed allowlist; do not use unrestricted future uploads of local data.
