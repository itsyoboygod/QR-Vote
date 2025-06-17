# QR Vote Blockchain

A blockchain-inspired voting system that uses QR codes to encode votes and stores the vote chain in a GitHub Gist for transparency and immutability.

## Overview

QR Vote is a lightweight, educational blockchain-based voting system that allows users to cast votes, generate QR codes, and maintain a tamper-evident chain stored in a GitHub Gist. Each vote is cryptographically linked using SHA-256 hashes, and QR codes can be scanned for verification. The system supports both offline and online modes, making it suitable for small-scale or learning purposes.

## Features

- Generates QR codes for each vote with encoded JSON data.
- Stores and syncs the vote chain with a GitHub Gist (`vote_chain.json`).
- Validates chain integrity using SHA-256 hashing.
- Scans QR codes to confirm vote data.
- Supports interactive or command-line vote input with dynamic candidate selection.
- Allows resetting or pruning the vote chain.
- Operates in offline and online modes with GitHub integration.

## Prerequisites

- Python 3.8+ (recommended 3.10+ for best compatibility).
- System Dependencies: `libzbar0` for QR code scanning.
- GitHub Account: Required for Gist storage (Personal Access Token with gist scope needed).

## Setup

### 1. Clone or Download the Repository

- Run:
 git clone <repository-url>
 cd qrvote</repository-url>

### 2. Install System Dependencies

- On Ubuntu-based systems:
 sudo apt-get update
 sudo apt-get install libzbar0
 
### 3. Set Up a Virtual Environment

- Create and activate:
  python3 -m venv qrvote_env
  source qrvote_env/bin/activate  # On Windows: qrvote_env\Scripts\activate
  
### 4. Install Python Dependencies

- Install required packages:
  pip install -r requirements.txt
  
  (Create `requirements.txt` with `python-dotenv`, `PyGithub`, `qrcode`, `pillow`, `pyzbar` if not present.)

### 5. Configure Environment Variables

- Create a `.env` file in the project root:
  touch .env
  
  - Add your GitHub Personal Access Token:
    GITHUB_TOKEN=your_github_token_here
    GIST_FILENAME=vote_chain.json
    GIST_DESCRIPTION=QR Vote Blockchain

    - Generate the token via GitHub settings under Developer settings with gist scope.

## Usage

Run the script from the `src` directory:
  cd src
  python qrvote.py

### Commands

- **Vote Interactively with Dynamic Candidates**:
  - Specify candidates using the `--candidates` flag:
    python qrvote.py --candidates "Candidate A" "Candidate B" "Candidate C"

- Follow the prompt to select a candidate from the list. Invalid inputs are rejected until a valid choice is made.

- **Cast a Vote via Command Line**:
- Example:
  python qrvote.py "Candidate A"
  
- **Scan QR Code**:
  python qrvote.py --scan qrcodes/qr_code_genesis_CandidateA_000001.png

- **Compare with Official Results**:
  python qrvote.py --compare '{"CandidateA": 100, "CandidateB": 150}'

- **Reset Chain**:
  python qrvote.py --reset
  
- **Prune a Vote**:
  python qrvote.py --prune "Candidate A"

### Expected Output

## For the first vote (genesis block):
<code>No GITHUB_TOKEN, running in offline mode.
Select your vote (Candidate A, Candidate B, Candidate C) or scan a QR with --scan: Candidate A
New vote added:
{
  "vote": "Candidate A",
  "timestamp": "2025-06-16T14:30:00.123456",
  "prev_hash": "genesis_hash",
  "hash": "new_hash_here"
}
Attempting to create directory: /src/qrcodes
Directory created or exists: True
Attempting to save QR code to: /src/qrcodes/qr_code_genesis_Candidate_A_000001.png
QR code saved successfully at: /src/qrcodes/qr_code_genesis_Candidate_A_000001.png
Updated Chain saved at: /src/vote_chain.json
Chain validation: Chain is valid</code>
- Subsequent votes link to the previous block’s hash.
- Online mode includes a Gist URL (e.g., `https://gist.github.com/username/1234567890abcdef`).

### Verify the Chain

- Check the Gist URL in the output to view `vote_chain.json`.
- Scan the generated QR code (e.g., with a smartphone app) to confirm the data.

## Directory Structure

- `qrvote/`
  - `src/` # Source code
    - `qrvote.py` # Main script
    - `qrcodes/` # Generated QR code images
    - `vote_chain.json` # Local vote chain file
  - `tests/` # Unit tests (to be added)
  - `qrvote_env/` # Virtual environment (ignored)
  - `.env` # Environment variables
  - `.gitignore` # Git ignore file
  - `LICENSE` # License file
  - `README.md` # This file
  - `requirements.txt` # Dependency list

## Contributing

- Fork the repository.
- Create a branch for your feature: `git checkout -b feature-name`.
- Commit changes: `git commit -m "Add feature-name"`.
- Push to the branch: `git push origin feature-name`.
- Open a pull request.

## License

This project is licensed under the [MIT License](LICENSE).

## Privacy

For privacy information, see [PRIVACY.md](PRIVACY.md).

## Troubleshooting

- **QR Code Not Saved**: Ensure `src/qrcodes/` is writable (`chmod -R u+w src/qrcodes`).
- **GitHub Errors**: Verify the `GITHUB_TOKEN` and network connectivity.
- **Dependency Issues**: Reinstall with `pip install -r requirements.txt`.
- **No Candidates**: Run with `--candidates` flag (e.g., `python qrvote.py --candidates "Candidate A" "Candidate B"`).

## Acknowledgments

- Built with guidance from xAI's Grok 3.
- Uses open-source libraries like `PyGithub`, `qrcode`, `pillow`, and `pyzbar`.

## Last Updated

02:28 PM -03, Monday, June 16, 2025