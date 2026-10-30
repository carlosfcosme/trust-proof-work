// Dynamic snippet runner: executes whatever snippet the agent composed.
const snippet = process.argv[2] || "1 + 1";
eval(snippet);
