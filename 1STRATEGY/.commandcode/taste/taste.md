# Taste (Continuously Learned by [CommandCode][cmd])

[cmd]: https://commandcode.ai/

# workflow
- Inspect existing codebase and architecture before proposing any changes. Confidence: 0.75
- Propose an implementation plan and await explicit approval before writing code. Confidence: 0.75
- Never invent or assume APIs, interfaces, or architecture; inspect the existing implementation when anything is ambiguous. Confidence: 0.75

# verification
- Run relevant tests/linters after implementation and show actual terminal output as evidence of success. Confidence: 0.75
- Never claim something works unless it has been executed successfully. Confidence: 0.75

# reporting
- Report all modified files after implementation with a brief explanation of each change. Confidence: 0.75
