# R221NATPD Natural Protected-Decision Labeling Protocol

This packet samples concrete protected-decision events from the existing R220
authority-input characterization. It does not sync datasets, run models, or
execute tools. The goal is to let a reviewer or independent labeler decide
whether each event really requires separate `agent`, `instruction`, `tool`, and
`env` authority issuers.

## Label Questions

For each sample in `sample_manifest.jsonl`, answer:

1. Is this a protected decision or a runtime-evidence event needed by a protected decision?
2. Which issuer classes are required: `agent`, `instruction`, `tool`, `env`?
3. Which protected fields does each issuer own?
4. Would it be unsafe for one issuer class to substitute for another?
5. Does this decision require runtime observer evidence rather than prompt text or tool metadata?
6. Is the observed checker denial a class-substitution attempt, or a different policy failure?

## Issuer Definitions

`agent` covers trusted user intent, object/sink selection, approval tokens,
budget root, task phase, and delegation root.

`instruction` covers endorsed system/developer/Skill/manual workflow procedure
inside a declared scope.

`tool` covers MCP/tool/cmd interface metadata, schema, credential scope, binary
descriptor, declared side effects, and sandbox contract.

`env` covers runtime observations: file existence, cwd, concrete values, tool
results, script outputs, process observations, and resource state.

## Use of Author Labels

`author_labels.codex.jsonl` is a project-author first pass. It is useful for
debugging the schema and checking that samples are labelable. It must not be
reported as blinded independent expert agreement.
