# Conclusion

An inline gateway can enforce a tool admission policy before the agent sees MCP tool metadata. The implemented proxy detects changes to a previously pinned definition, screens for inconsistency between stated and declared capabilities, and rejects calls to removed tools while forwarding normal requests for approved ones.

In a preliminary first-sight replay with Qwen3 8B, deterministic filtering and the decision ladder reduced judged attack success from 59/300 to 37/300. That corresponds to a paired reduction of 7.3 percentage points. The baseline also removed 3/128 authentic held-out tools, and the external authentic-only study showed that quarantine can amplify the availability cost. These results quantify protection and disruption within the evaluated settings.

The frozen L3 screen identified many poisoned examples that the existing gateway would serve. Schema missingness and the concentration of external flags on zero-parameter tools make independent validation necessary. L4 demonstrates a local, structured review of uncertain metadata. A fresh labeled evaluation and a paired enforcement experiment are needed before assigning either advisory layer a role in admission.
