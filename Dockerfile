# Glama introspection bridge for the TLS Radar MCP server.
#
# TLS Radar is a HOSTED, remote MCP server at https://tlsradar.com/api/v1/mcp
# (Streamable HTTP) — there is no local server binary to run. This image is a thin
# stdio<->remote bridge (mcp-remote) so directories like Glama can "start a server"
# and run introspection (tools/list) against the live endpoint. The public
# scan/cert tools list without authentication, so introspection succeeds.
#
# This Dockerfile exists ONLY for registry introspection/scoring. End users do not
# run it — they install the plugin (see README) or connect to the hosted endpoint.
FROM node:22-alpine
RUN npm install -g mcp-remote@latest
ENTRYPOINT ["mcp-remote", "https://tlsradar.com/api/v1/mcp"]
