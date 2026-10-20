# Privacy and security boundaries

This is a **single-user local alpha**, not a multi-tenant coaching service. The operating-system account is the trust boundary. Pseudonymous athlete IDs organize folders and prevent accidental cross-athlete lookups; they are not credentials. Anyone controlling the process/workspace can access all authorized athletes. Encryption at rest, RBAC, identity verification, signed consent, tamper-proof audit logs and remote authentication are not implemented.

## Data flow

- Direct CLI analysis reads the specified local file and emits JSON. Authorization is the coach's responsibility.
- Workspace ingestion requires an active local consent record; saves normalized samples, original source hash, integrity hash and retained metadata. It does not copy the original binary or store platform credentials.
- All workspace reads recheck consent. Athlete/workout IDs are constrained; path traversal and symlinks are rejected. POSIX folders/files use 0700/0600; Windows permission bits are not a substitute for NTFS ACL review.
- Summary route coordinates are omitted by default. Absolute timestamps, source hashes, lap labels, metadata and coach notes can still be identifying. Reports are minimized, not anonymized. Review before uploading to any AI provider.
- MCP exposes read-only local tools and no arbitrary file-path arguments. The AI host can still send tool results to its model provider under that host's settings. Local engine processing does not make the entire AI workflow offline.
- Weather sends rounded GPS coordinates and dates only with explicit CLI network opt-in. Cache files retain the provider's returned coordinates and dates. Coordinate rounding is not anonymization. Cache integrity checks detect accidental body modification, not malicious local-owner manipulation.
- Revocation blocks reads and removes normalized workouts and context under that athlete folder. It retains an unauthorized consent marker. Original files, exports, weather caches and backups require separate deletion. No guaranteed forensic erasure.

Treat all file/metadata/note text as untrusted data. No ingestion metadata executes shell commands or prompts. Review file origin and keep dependencies patched. XML external entities are blocked; FIT uses strict CRC/error handling and bounded input size. XML tree parsing and several analyses are in-memory and are not designed to withstand hostile concurrent requests. No independent security audit or regulatory compliance certification has occurred.

The tests exercise path traversal rejection, symlink rejection, missing/revoked consent, same-athlete lookups, private POSIX modes, normalized-data integrity, weather network opt-in, unit matching and MCP error paths. These tests are evidence of specific controls, not a security audit.
