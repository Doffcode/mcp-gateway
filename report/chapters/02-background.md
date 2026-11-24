# Background and related work

## MCP tool discovery and invocation

MCP defines a client/server interface for discovering and calling tools. A client retrieves tool definitions using `tools/list` and invokes a named tool with arguments using `tools/call`. The specification defines the tool name, description, and input schema alongside other fields, including optional annotations and output schemas. A tool description explains purpose in natural language. The input schema describes the shape of acceptable arguments. Both can provide context to the model that selects the tool [@mcp2025tools].

A schema can show that an argument is expected to contain a path or an endpoint. It cannot establish that a tool is authorized to access a particular resource or that the server implementation behaves as described. This distinction motivates a metadata consistency check before selection and separate runtime authorization at the host or tool boundary.

## Metadata poisoning and evaluation

MCPTox provides tool-metadata poisoning cases based on real server definitions and records model responses to those cases [@wang2026mcptox]. Its tool-list prompt format supports a controlled comparison in which the tool blocks exposed to the model can be varied while retaining the user's request. This thesis uses its released data and a separate, server-grouped split.

MCPSecBench considers security across several MCP components. Its broader taxonomy helps locate this thesis within the server-metadata surface. Runtime tool output, transport behavior, and other MCP surfaces require different evaluation designs [@yang2025mcpsecbench].

MCP-Guard combines static detection, learned representations, and a model reviewer [@xing2026mcp]. In this thesis the decision ladder has explicit enforcement authority and both learned stages report findings, which allows the evaluation to distinguish advice from a denial. Published results from other defenses use different corpora and decision rules. They are treated as related evidence without establishing a comparative ranking.

An audit of CASCADE illustrates how corpus construction and the mapping of review decisions to binary outcomes can change reported effectiveness. This motivates the separate reporting of screening flags and actual admission decisions in this work [@turgut2026evaluating].
