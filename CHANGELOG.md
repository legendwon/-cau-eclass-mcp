# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-09

### Added
- Initial public release
- SSO authentication with CAU portal using RSA password encryption
- CAU-ON API client for e-class platform
- Cross-platform credential management using OS keyring
- Fallback to environment variables (CAU_USERNAME, CAU_PASSWORD)
- Interactive credential prompt for first-time setup
- MCP server implementation with 4 tools:
  - `get_dashboard`: View all active courses with metadata
  - `list_course_announcements`: List announcements for specific course
  - `list_assignments`: List assignments with submission status
  - `get_lecture_modules`: View weekly lecture modules with attendance status
- Automatic session management with file-based caching
- Migration helper for users with old Windows DPAPI credentials

### Technical Details
- HTTP/2 support via httpx for CAU-ON API compatibility
- Client-side RSA decryption (PKCS1v15) for password submission
- Canvas JSON security handling (while(1); prefix stripping)
- Session type detection (API-enabled vs non-API-enabled cookies)

### Dependencies
- Python 3.10+
- mcp >= 1.0.0
- requests >= 2.31.0
- httpx[http2] >= 0.27.0
- beautifulsoup4 >= 4.12.0
- lxml >= 5.0.0
- cryptography >= 42.0.0
- keyring >= 24.0.0
