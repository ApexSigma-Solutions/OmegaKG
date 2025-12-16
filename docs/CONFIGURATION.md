# Omega KG Configuration Guide

This document provides comprehensive configuration guidance for the Omega KG system.

## Environment Variables

### Core Configuration

| Variable | Description | Default | Valid Range |
|----------|-------------|---------|-------------|
| `OMEGA_ENV` | Environment marker (dev/prod) | `dev` | `dev`, `prod` |
| `VAULT_PATH` | Path to Obsidian vault | `./vault` | Any valid path |
| `NEO4J_URI` | Neo4j database URI | `bolt://localhost:7687` | Valid Neo4j URI |
| `NEO4J_USER` | Neo4j username | `neo4j` | Any string |
| `NEO4J_PASSWORD` | Neo4j password | `password` | Any string |

### Authentication Configuration

| Variable | Description | Default | Valid Range |
|----------|-------------|---------|-------------|
| `CAPTURE_SERVER_API_KEYS` | Comma-separated API keys for Chrome extension | `test-key-1,test-key-2` | Comma-separated strings |
| `JWT_SECRET_KEY` | Secret key for JWT token generation | `your-secret-key` | Strong random string |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` | `HS256`, `HS384`, `HS512` |
| `JWT_EXPIRATION_MINUTES` | JWT token expiration time | `60` | Positive integer |

### Percolation Engine Configuration

| Variable | Description | Default | Valid Range |
|----------|-------------|---------|-------------|
| `PERCOLATION_SIMILARITY_THRESHOLD` | Similarity threshold for creating relationships | `0.8` | `0.0` - `1.0` |

## Percolation Similarity Threshold

The `PERCOLATION_SIMILARITY_THRESHOLD` environment variable controls the minimum similarity score required for the percolation engine to create relationships between tasks based on vector embeddings.

### How It Works

- **Range**: 0.0 (no similarity required) to 1.0 (exact match required)
- **Default**: 0.8 (80% similarity)
- **Usage**: Applied in Cypher queries using `vector.similarity` function

### Tuning Guidance

#### High Threshold (0.9 - 1.0)
- **Use Case**: When you want very strict similarity matching
- **Result**: Fewer relationships, higher precision
- **Risk**: May miss relevant connections

#### Medium Threshold (0.7 - 0.89)
- **Use Case**: Balanced approach (recommended)
- **Result**: Good balance of precision and recall
- **Default**: 0.8 falls in this range

#### Low Threshold (0.0 - 0.69)
- **Use Case**: When you want to capture more potential relationships
- **Result**: More relationships, higher recall
- **Risk**: May create irrelevant connections

### Configuration Examples

```bash
# Strict similarity matching
PERCOLATION_SIMILARITY_THRESHOLD=0.95

# Balanced approach (default)
PERCOLATION_SIMILARITY_THRESHOLD=0.8

# Permissive matching
PERCOLATION_SIMILARITY_THRESHOLD=0.6
```

### Validation

The system validates that the threshold is within the valid range (0.0-1.0) at startup. Invalid values will cause the application to fail fast with a clear error message.

### Performance Considerations

- Lower thresholds may increase query execution time due to more relationship candidates
- Higher thresholds may reduce the number of relationships created
- The threshold is applied at query time, not during embedding generation

## Bitwarden Integration

For production deployments, sensitive configuration should be managed through Bitwarden:

### Required Secrets

1. **BWS Access Token**: `BWS_ACCESS_TOKEN`
2. **Linear Webhook Secret**: `LINEAR_WEBHOOK_SECRET_PRD_ID`
3. **Database Credentials**: Stored as Bitwarden secrets

### Setup Steps

1. Create Bitwarden account and organization
2. Generate BWS access token
3. Create secrets for sensitive configuration
4. Configure environment variables with secret IDs

See `docs/BITWARDEN_INTEGRATION.md` for detailed setup instructions.

## Environment-Specific Configuration

### Development Environment
```bash
OMEGA_ENV=dev
PERCOLATION_SIMILARITY_THRESHOLD=0.7  # More permissive for testing
```

### Production Environment
```bash
OMEGA_ENV=prod
PERCOLATION_SIMILARITY_THRESHOLD=0.85  # Stricter for production
```

## Troubleshooting

### Common Issues

1. **Invalid threshold value**: Ensure threshold is between 0.0 and 1.0
2. **Missing environment variable**: Check `.env` file exists and is properly formatted
3. **Bitwarden connection failure**: Verify `BWS_ACCESS_TOKEN` is valid

### Validation Tools

Run the startup validation script to check configuration:
```bash
poetry run python -c "from omega_kg.settings import Settings; Settings()"
```

This will validate all configuration and report any issues.