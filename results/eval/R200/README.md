# Expert Oracle Label Packet

Run: R200
Labeler templates: expert_a, expert_b

This directory is an input packet for E2. It does not contain expert labels.

## Files

- `label_templates/<labeler>/<sample_id>.json`: TODO-filled templates.
- `adjudication_sheet.csv`: paths and status fields for adjudication.
- `template_validation_report.csv`: schema-shape validation with placeholders allowed.

## Required Workflow

1. Each labeler independently replaces every TODO in their template.
2. Validate completed labels with `python scripts/prepare_expert_oracle_labels.py --validate-label-dir <filled-label-dir> --output-dir <validation-output-dir>`.
3. Adjudicate disagreements into `adjudicated_labels/<sample_id>.json`.
4. Score baselines only against adjudicated labels.
