from github import Github, InputFileContent
import json
import hashlib
import datetime
import qrcode
import base64
from pyzbar.pyzbar import decode
from PIL import Image
import sys
import os

# Configuration
from dotenv import load_dotenv
import os
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "default_token_if_not_set")
GIST_FILENAME = os.getenv("GIST_FILENAME", "vote_chain.json")
GIST_DESCRIPTION = os.getenv("GIST_DESCRIPTION", "QR Vote Blockchain MVP")

def hash_block(block):
    """Calculate SHA-256 hash of a block"""
    block_string = json.dumps(block, sort_keys=True).encode()
    return hashlib.sha256(block_string).hexdigest()

def load_chain(g):
    """Load the vote chain from Gist"""
    try:
        user = g.get_user()
        for gist in user.get_gists():
            if GIST_FILENAME in gist.files:
                content = gist.files[GIST_FILENAME].content
                return gist, json.loads(content) if content else []
        return None, []
    except Exception as e:
        print(f"Error loading Gist: {e}")
        return None, []

def add_vote(vote, prev_hash):
    """Create a new vote block"""
    block = {
        "vote": vote,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "prev_hash": prev_hash
    }
    block["hash"] = hash_block(block)
    return block

def create_qr_code(block):
    """Generate a QR code for the vote block"""
    try:
        block_string = json.dumps(block)
        encoded_data = base64.b64encode(block_string.encode()).decode()
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4
        )
        qr.add_data(encoded_data)
        qr.make(fit=True)
        qr_filename = f"vote_{block['hash'][:8]}.png"
        qr_path = os.path.join("qrcodes", qr_filename)  # Construct path to /qrcodes
        os.makedirs("qrcodes", exist_ok=True)          # Create /qrcodes if it doesn't exist
        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_image.save(qr_path)
        return qr_path
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None

def scan_qr_code(qr_filename):
    """Scan a QR code and decode vote data"""
    try:
        image = Image.open(qr_filename)
        decoded_objects = decode(image)
        if not decoded_objects:
            return None
        encoded_data = decoded_objects[0].data.decode()
        vote_string = base64.b64decode(encoded_data).decode()
        return json.loads(vote_string)
    except Exception as e:
        print(f"Error scanning QR code: {e}")
        return None

def validate_chain(chain):
    """Validate the vote chain"""
    try:
        for i, block in enumerate(chain[1:], 1):
            if block["prev_hash"] != chain[i-1]["hash"]:
                return False, f"Invalid previous hash at block {i}"
            block_copy = block.copy()
            current_hash = block_copy.pop("hash")
            calculated_hash = hash_block(block_copy)
            if current_hash != calculated_hash:
                return False, f"Invalid hash at block {i}"
        return True, "Chain is valid"
    except Exception as e:
        return False, f"Validation error: {e}"

def save_chain(g, gist, chain):
    """Save the vote chain to Gist"""
    try:
        content = json.dumps(chain, indent=2)
        if gist:
            gist.edit(files={GIST_FILENAME: InputFileContent(content)})
        else:
            user = g.get_user()
            gist = user.create_gist(
                public=False,
                files={GIST_FILENAME: InputFileContent(content)},
                description=GIST_DESCRIPTION
            )
        return gist.html_url
    except Exception as e:
        print(f"Error saving Gist: {e}")
        return None

def main():
    # Initialize GitHub client
    try:
        g = Github(GITHUB_TOKEN)
    except Exception as e:
        print(f"Error initializing GitHub client: {e}")
        sys.exit(1)

    # Load existing chain
    gist, chain = load_chain(g)
    if chain is None:
        print("Failed to load chain. Exiting.")
        sys.exit(1)

    # Get vote from command-line argument or prompt
    if len(sys.argv) > 1:
        vote = sys.argv[1]
    else:
        vote = input("Enter your vote (e.g., YES, NO, Candidate A): ")

    # Validate vote input
    if not vote.strip():
        print("Vote cannot be empty.")
        sys.exit(1)

    # Add new vote
    prev_hash = chain[-1]["hash"] if chain else "genesis_hash"
    new_block = add_vote(vote.strip(), prev_hash)

    # Generate QR code
    qr_filename = create_qr_code(new_block)
    if not qr_filename:
        print("Failed to generate QR code. Vote not saved.")
        sys.exit(1)

    # Add block to chain
    chain.append(new_block)

    # Save updated chain
    url = save_chain(g, gist, chain)
    if not url:
        print("Failed to save chain to Gist.")
        sys.exit(1)

    # Validate chain
    is_valid, message = validate_chain(chain)
    
    # Print results
    print("New vote added:")
    print(json.dumps(new_block, indent=2))
    print(f"QR code saved as: {qr_filename}")
    print(f"Updated Chain Gist URL: {url}")
    print(f"Chain validation: {message}")

    # Test scanning the QR code
    scanned_block = scan_qr_code(qr_filename)
    if scanned_block:
        print("Scanned QR code data:")
        print(json.dumps(scanned_block, indent=2))
    else:
        print("Failed to scan QR code.")

if __name__ == "__main__":
    main()