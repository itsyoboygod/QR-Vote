# QR Vote

A blockchain-inspired voting system that uses QR codes to encode votes and stores the vote chain in a GitHub Gist for transparency and immutability.

## Overview

QR Vote allows users to cast votes, generate QR codes representing those votes, and maintain a tamper-evident chain stored in a GitHub Gist. Each vote is linked via SHA-256 hashes, and QR codes can be scanned to verify the data. The system is designed for educational or small-scale voting use cases.

## Features

- Generates QR codes for each vote with encoded JSON data.
- Stores the vote chain in a GitHub Gist (vote_chain.json).
- Validates chain integrity using SHA-256 hashing.
- Scans QR codes to confirm vote data.
- Supports command-line or interactive vote input.

## Prerequisites

- Python 3.8+ (recommended 3.8 due to current setup, though upgrading to 3.10+ is advised).
- System Dependencies: libzbar0 for QR code scanning.
- GitHub Account: For Gist storage (requires a Personal Access Token with gist scope).

## Setup

### 1. Clone or Download the Repository

- Run the following commands:
  - git clone <repository-url>
  - cd qrvote

### 2. Install System Dependencies

- On Ubuntu-based systems, execute:
  - sudo apt-get update
  - sudo apt-get install libzbar0

### 3. Set Up a Virtual Environment

- Create and activate the virtual environment with:
  - python3 -m venv qrvote_env
  - source qrvote_env/bin/activate

### 4. Install Python Dependencies

- Install required packages with:
  - pip install -r requirements.txt

### 5. Configure Environment Variables

- Create a .env file in the project root by running:
  - touch .env
- Add your GitHub Personal Access Token with the following content:
  - GITHUB_TOKEN=your_github_token_here
  - GIST_FILENAME=vote_chain.json
  - GIST_DESCRIPTION=QR Vote Blockchain MVP
- Ensure the token has gist scope (generate via GitHub settings under Developer settings).

## Usage

### Run the Script

- Activate the virtual environment:
  - source qrvote_env/bin/activate
- Cast a vote with a command-line argument:
  - python src/qrvote.py "YES"
- Or run interactively (prompts for input):
  - python src/qrvote.py

### Expected Output

For the first vote (genesis block):
- New vote added:
  - {
    "vote": "YES",
    "timestamp": "2025-06-11T11:07:00.123456",
    "prev_hash": "genesis_hash",
    "hash": "a1622f0b3f59353b39ee8bb7cca9a377576228b03957ee83b28a356822a3a8ef"
    }
- QR code saved as: qrcodes/vote_a1622f0b.png
- Updated Chain Gist URL: https://gist.github.com/username/1234567890abcdef
- Chain validation: Chain is valid
- Scanned QR code data:
  - {
    "vote": "YES",
    "timestamp": "2025-06-11T11:07:00.123456",
    "prev_hash": "genesis_hash",
    "hash": "a1622f0b3f59353b39ee8bb7cca9a377576228b03957ee83b28a356822a3a8ef"
    }

Subsequent votes will link to the previous block’s hash.

### Verify the Chain

- Check the Gist URL in the output to view the vote_chain.json file.
- Scan the generated QR code (e.g., with a smartphone app) to confirm the data.

## Directory Structure

- qrvote/
  - src/ # Source code
    - qrvote.py # Main script
  - qrcodes/ # Generated QR code images
  - tests/ # Unit tests (to be added)
  - qrvote_env/ # Virtual environment (ignored)
  - .env # Environment variables
  - .gitignore # Git ignore file
  - LICENSE # License file
  - README.md # This file
  - requirements.txt # Dependency list

## Contributing

- Fork the repository.
- Create a branch for your feature: git checkout -b feature-name.
- Commit changes: git commit -m "Add feature-name".
- Push to the branch: git push origin feature-name.
- Open a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Privacy

For privacy information, see PRIVACY.md.

## Troubleshooting

- QR Code Not Saved: Ensure qrcodes/ is writable (chmod -R u+w qrcodes).
- GitHub Errors: Verify the GITHUB_TOKEN and network connectivity.
- Dependency Issues: Reinstall with pip install -r requirements.txt.

## Acknowledgments

- Built with guidance from xAI's Grok 3.
- Uses open-source libraries like PyGithub, qrcode, and pyzbar.

## Last Updated

11:07 AM -03, Wednesday, June 11, 2025