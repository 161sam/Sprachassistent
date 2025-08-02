# Headscale Integration

The backend can optionally query a Headscale instance to discover connected nodes.

## Configuration

Set the following variables in your `.env`:

```env
HEADSCALE_API=http://localhost:8080/api
HEADSCALE_TOKEN=changeme
```

`HEADSCALE_API` should point to the Headscale API base URL. If authentication is required, provide
`HEADSCALE_TOKEN` which will be sent as Bearer token.

## Behaviour

On startup the WebSocket server tries to contact `HEADSCALE_API` and logs the available node IDs. This
allows the assistant to adapt to the current network topology.

## Troubleshooting

- Ensure the Headscale service is reachable from the machine running the backend.
- Tokens can be created via `headscale apikeys create` if the API is protected.
