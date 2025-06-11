# Privacy Policy

## Overview

The QR Vote system is designed for educational or demonstration purposes and handles vote data in a transparent manner. This privacy policy outlines how data is collected, stored, and protected.

## Data Collection

- Vote Data: The system collects vote values (e.g., "YES", "NO") along with timestamps and cryptographic hashes. This data is encoded into QR codes and stored in a GitHub Gist.
- No Personal Information: The system does not collect personally identifiable information (PII) such as names, emails, or IP addresses unless explicitly provided by the user (e.g., via a custom vote input).
- GitHub Integration: The system uses a GitHub Personal Access Token to interact with the Gist API. This token is stored in a .env file and should be kept secure.

## Data Storage

- GitHub Gist: Vote chain data is stored publicly in a GitHub Gist (vote_chain.json) unless configured as private. Users are responsible for setting the Gist visibility.
- Local Storage: QR code images are saved locally in the qrcodes/ directory on the user’s machine.
- Retention: Data is retained as long as the Gist exists or until manually deleted by the user.

## Data Protection

- Encryption: Vote data is hashed using SHA-256, but no end-to-end encryption is applied. The system relies on GitHub’s security for Gist storage.
- Access Control: Access to the Gist is controlled by the GitHub token. Users should protect this token and avoid sharing it.
- QR Code Security: QR codes are scanned locally and do not transmit data unless shared by the user.

## User Responsibilities

- Users must secure their GitHub token and .env file to prevent unauthorized access.
- Avoid including sensitive information in vote data.
- Regularly review and delete Gists if privacy is a concern.

## Limitations

- This is not a production-ready voting system. It lacks advanced security features (e.g., digital signatures, voter authentication) and should not be used for official elections.
- Data in the Gist is accessible to anyone with the URL if set to public.

## Contact

For questions or concerns about privacy, contact ItsYoBoyGod at marcus.aguiar11+github@gmail.com .

## Last Updated

11:07 AM -03, Wednesday, June 11, 2025