"""Network transport: each bot is a separate process/server; the coordinator talks
to them over HTTP and never sees their private sheets. Stdlib only."""
