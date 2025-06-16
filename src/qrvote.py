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
load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Set base directory to script location
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GIST_FILENAME = os.getenv("GIST_FILENAME", "vote_chain.json")
GIST_DESCRIPTION = os.getenv("GIST_DESCRIPTION", "QR Vote Street Talk Blockchain")
ELECTION_END_TIME = datetime.datetime(2025, 6, 15, 18, 0, 0, tzinfo=datetime.timezone.utc)  # Example: June 15, 2025, 6:00 PM UTC

def hash_block(block):
    """Calculate SHA-256 hash of a block"""
    block_string = json.dumps(block, sort_keys=True).encode()
    return hashlib.sha256(block_string).hexdigest()

def load_chain(g):
    """Load the vote chain from Gist or local file"""
    try:
        if g:  # Online mode
            user = g.get_user()
            for gist in user.get_gists():
                if GIST_FILENAME in gist.files:
                    content = gist.files[GIST_FILENAME].content
                    return gist, json.loads(content) if content else []
        local_path = os.path.join(BASE_DIR, "vote_chain.json")
        if os.path.exists(local_path):
            with open(local_path, "r") as f:
                content = f.read().strip()
                if not content:
                    return None, []
                return None, json.loads(content)
        return None, []
    except Exception as e:
        print(f"Error loading chain (falling back to local): {e}")
        local_path = os.path.join(BASE_DIR, "vote_chain.json")
        if os.path.exists(local_path):
            with open(local_path, "r") as f:
                content = f.read().strip()
                if not content:
                    return None, []
                return None, json.loads(content)
        return None, []

def sync_local_chain(g, gist, local_chain):
    """Sync local vote_chain.json with the latest Gist data, merging with local changes"""
    if g and gist:
        try:
            content = gist.files[GIST_FILENAME].content
            gist_chain = json.loads(content) if content else []
            merged_chain = merge_chains(local_chain, gist_chain)
            local_path = os.path.join(BASE_DIR, "vote_chain.json")
            with open(local_path, "w") as f:
                json.dump(merged_chain, f, indent=2)
            print("Local chain synced with Gist.")
            return merged_chain
        except Exception as e:
            print(f"Error syncing local chain: {e}")
            return local_chain
    return local_chain

def add_vote(candidate, prev_hash):
    """Create a new vote block"""
    block = {
        "vote": candidate,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "prev_hash": prev_hash
    }
    block["hash"] = hash_block(block)
    return block

def create_qr_code(candidate):
    """Generate a QR code for a candidate"""
    try:
        qr_data = f"genesis:{candidate}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_filename = f"qr_code_genesis_{candidate.replace(' ', '_')}_000001.png"
        qr_path = os.path.join(BASE_DIR, "qrcodes", qr_filename)
        qr_dir = os.path.join(BASE_DIR, "qrcodes")
        print(f"Attempting to create directory: {qr_dir}")
        os.makedirs(qr_dir, exist_ok=True)
        print(f"Directory created or exists: {os.path.exists(qr_dir)}")
        qr_image = qr.make_image(fill_color="black", back_color="white")
        print(f"Attempting to save QR code to: {qr_path}")
        qr_image.save(qr_path)
        print(f"QR code saved successfully at: {qr_path}")
        return qr_path
    except Exception as e:
        print(f"Error generating QR code: {str(e)}")
        return None

def scan_and_vote(qr_filename):
    """Scan a QR code and handle vote"""
    try:
        image = Image.open(qr_filename)
        decoded_objects = decode(image)
        if not decoded_objects:
            return None
        qr_data = decoded_objects[0].data.decode()
        if qr_data.startswith("genesis:"):
            candidate = qr_data[len("genesis:"):]
            current_time = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
            if current_time > ELECTION_END_TIME:
                print(f"Election ended at {ELECTION_END_TIME}. No further votes accepted.")
                return None
            return candidate
        return None
    except Exception as e:
        print(f"Error scanning QR code: {e}")
        return None

def validate_chain(chain):
    """Validate the vote chain with detailed output"""
    try:
        for i, block in enumerate(chain[1:], 1):
            if block["prev_hash"] != chain[i-1]["hash"]:
                print(f"Validation failed at block {i}: prev_hash {block['prev_hash']} != {chain[i-1]['hash']}")
                return False, f"Invalid previous hash at block {i}"
            block_copy = block.copy()
            current_hash = block_copy.pop("hash")
            calculated_hash = hash_block(block_copy)
            if current_hash != calculated_hash:
                print(f"Validation failed at block {i}: stored hash {current_hash} != calculated {calculated_hash}")
                return False, f"Invalid hash at block {i}"
        return True, "Chain is valid"
    except Exception as e:
        return False, f"Validation error: {e}"

def save_chain(g, gist, chain):
    """Save the vote chain to Gist or local file"""
    try:
        content = json.dumps(chain, indent=2)
        local_path = os.path.join(BASE_DIR, "vote_chain.json")
        with open(local_path, "w") as f:  # Always save to local file
            json.dump(chain, f, indent=2)
        if g and gist:  # Online mode
            gist.edit(files={GIST_FILENAME: InputFileContent(content)})
            return gist.html_url
        return local_path
    except Exception as e:
        print(f"Error saving chain: {e}")
        return None

def merge_chains(local_chain, gist_chain):
    """Merge local and Gist chains, deduplicating and sorting by timestamp"""
    if not gist_chain and not local_chain:
        return []
    combined_chain = gist_chain + local_chain if gist_chain else local_chain
    if not combined_chain:
        return []
    # Track unique vote and timestamp combinations
    seen = set()
    unique_chain = []
    for block in combined_chain:
        key = (block["vote"], block["timestamp"])
        if key not in seen:
            unique_chain.append(block)
            seen.add(key)
    # Sort by timestamp to ensure chronological order
    unique_chain = sorted(unique_chain, key=lambda x: x["timestamp"])
    # Re-link prev_hash to ensure chain integrity
    for i in range(1, len(unique_chain)):
        unique_chain[i]["prev_hash"] = unique_chain[i-1]["hash"]
    if unique_chain:
        unique_chain[0]["prev_hash"] = "genesis_hash"
    return unique_chain

def prune_chain(chain, vote_to_remove):
    """Remove a specific vote and rebuild the chain"""
    if not chain:
        return []
    # Filter out the vote to remove
    remaining_chain = [block for block in chain if block["vote"] != vote_to_remove]
    if not remaining_chain:
        return []
    # Re-link prev_hash and recalculate hashes
    for i in range(len(remaining_chain)):
        remaining_chain[i]["prev_hash"] = remaining_chain[i-1]["hash"] if i > 0 else "genesis_hash"
        remaining_chain[i]["hash"] = hash_block(remaining_chain[i])
    return remaining_chain

def get_vote_counts(chain):
    """Calculate vote counts per candidate"""
    counts = {}
    for block in chain:
        counts[block["vote"]] = counts.get(block["vote"], 0) + 1
    return counts

def compare_with_official(official_results):
    """Compare QR votes with official results"""
    chain = load_chain(None)[1]  # Load local chain for simplicity
    qr_counts = get_vote_counts(chain)
    print("\nQR Vote Counts vs Official Results:")
    for candidate, count in qr_counts.items():
        official_count = official_results.get(candidate, 0)
        difference = count - official_count
        print(f"{candidate}: QR Votes = {count}, Official Votes = {official_count}, Difference = {difference}")

def reset_chain():
    """Reset the chain to empty"""
    local_path = os.path.join(BASE_DIR, "vote_chain.json")
    if os.path.exists(local_path):
        os.remove(local_path)
    print("Local chain reset. Gist will be updated on next online run.")

def main():
    # Initialize GitHub client
    g = None
    try:
        if GITHUB_TOKEN:
            g = Github(GITHUB_TOKEN)
            print("GitHub authenticated, running in online mode.")
        else:
            print("No GITHUB_TOKEN, running in offline mode.")
    except Exception:
        print("GitHub authentication failed, running in offline mode.")

    # Load existing chains
    gist, gist_chain = load_chain(g) if g else (None, [])
    _, local_chain = load_chain(None)  # Force local load
    chain = merge_chains(local_chain, gist_chain)

    # Sync local chain with Gist if online
    if g and gist:
        chain = sync_local_chain(g, gist, local_chain)

    # Parse candidates from command line
    allowed_candidates = []
    if "--candidates" in sys.argv:
        candidates_index = sys.argv.index("--candidates")
        allowed_candidates = sys.argv[candidates_index + 1:]
        # Remove candidates from sys.argv to avoid misinterpretation by other flags
        sys.argv[candidates_index:candidates_index + len(allowed_candidates) + 1] = []

    # Check for scan mode, compare mode, reset, prune, or vote input
    if len(sys.argv) > 1 and sys.argv[1] == "--scan":
        if len(sys.argv) > 2:
            qr_filename = sys.argv[2]
            candidate = scan_and_vote(qr_filename)
            if candidate:
                prev_hash = chain[-1]["hash"] if chain else "genesis_hash"
                new_block = add_vote(candidate, prev_hash)
                chain.append(new_block)
                url = save_chain(g, gist, chain)
                is_valid, message = validate_chain(chain)
                print(f"Vote added for {candidate}")
                print(f"New block: {json.dumps(new_block, indent=2)}")
                print(f"Chain saved at: {url}")
                print(f"Chain validation: {message}")
            else:
                print("Invalid QR code or election has ended.")
        else:
            print("Please provide a QR code filename with --scan, e.g., --scan qrcodes/qr_code_genesis_CandidateA_000001.png")
    elif len(sys.argv) > 1 and sys.argv[1] == "--compare":
        if len(sys.argv) > 2:
            try:
                official_results = json.loads(sys.argv[2])  # Expect JSON string like '{"CandidateA": 100, "CandidateB": 150}'
                compare_with_official(official_results)
            except json.JSONDecodeError:
                print("Invalid official results format. Use JSON, e.g., '{\"CandidateA\": 100, \"CandidateB\": 150}'")
        else:
            print("Please provide official results with --compare, e.g., --compare '{\"CandidateA\": 100, \"CandidateB\": 150}'")
    elif len(sys.argv) > 1 and sys.argv[1] == "--reset":
        reset_chain()
    elif len(sys.argv) > 1 and sys.argv[1] == "--prune":
        if len(sys.argv) > 2:
            vote_to_remove = sys.argv[2]
            chain = prune_chain(chain, vote_to_remove)
            url = save_chain(g, gist, chain)
            is_valid, message = validate_chain(chain)
            print(f"Removed vote for {vote_to_remove}")
            print(f"Updated Chain saved at: {url}")
            print(f"Chain validation: {message}")
        else:
            print("Please provide a vote to remove with --prune, e.g., --prune 'Candidate A'")
    else:
        # Use provided candidates or prompt if none given
        if not allowed_candidates:
            print("No candidates provided. Please run with --candidates flag, e.g., python qrvote.py --candidates 'Candidate A' 'Candidate B'")
            return
        while True:
            vote = input(f"Select your vote ({', '.join(allowed_candidates)}) or scan a QR with --scan: ").strip()
            if vote in allowed_candidates:
                break
            print(f"Invalid choice. Please select one of {', '.join(allowed_candidates)}.")
        prev_hash = chain[-1]["hash"] if chain else "genesis_hash"
        new_block = add_vote(vote, prev_hash)
        chain.append(new_block)
        url = save_chain(g, gist, chain)
        is_valid, message = validate_chain(chain)
        print("New vote added:")
        print(json.dumps(new_block, indent=2))
        qr_path = create_qr_code(vote)
        if qr_path:
            print(f"QR code saved as: {os.path.relpath(qr_path, BASE_DIR)}")
        else:
            print("Failed to generate QR code.")
        print(f"Updated Chain saved at: {url}")
        print(f"Chain validation: {message}")

if __name__ == "__main__":
    main()