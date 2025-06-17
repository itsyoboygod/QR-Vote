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

# Try to import stegano for steganography, fall back if unavailable
try:
    from stegano import lsb
    HAS_STEGANOGRAPHY = True
except ImportError:
    HAS_STEGANOGRAPHY = False

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
        print(f"Error loading chain: {e}")
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

def create_qr_code(candidate, steganography_message=None):
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
        os.makedirs(qr_dir, exist_ok=True)
        
        # Generate QR image
        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_image.save(qr_path)

        # Convert to RGB if necessary for steganography
        if HAS_STEGANOGRAPHY and steganography_message:
            qr_image_rgb = qr_image.convert("RGB")
            qr_image_rgb.save(qr_path)
            MIN_LENGTH = 1
            MAX_LENGTH = 100
            if not (MIN_LENGTH <= len(steganography_message) <= MAX_LENGTH):
                return qr_path
            stego_path = os.path.join(qr_dir, f"stego_{qr_filename}")
            secret_image = lsb.hide(qr_path, steganography_message)
            secret_image.save(stego_path)
            return stego_path
        return qr_path
    except Exception as e:
        print(f"Error generating QR code or steganography: {e}")
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

def validate_chain(chain, verbose=False):
    """Validate the vote chain with optional verbose output"""
    try:
        for i, block in enumerate(chain[1:], 1):
            if block["prev_hash"] != chain[i-1]["hash"]:
                if verbose:
                    print(f"Validation failed at block {i}: prev_hash {block['prev_hash']} != {chain[i-1]['hash']}")
                return False, f"Invalid previous hash at block {i}"
            block_copy = block.copy()
            current_hash = block_copy.pop("hash")
            calculated_hash = hash_block(block_copy)
            if current_hash != calculated_hash:
                if verbose:
                    print(f"Validation failed at block {i}: stored hash {current_hash} != calculated {calculated_hash}")
                return False, f"Invalid hash at block {i}"
        return True, "Chain is valid"
    except Exception as e:
        if verbose:
            print(f"Validation error: {e}")
        return False, "Validation error"

def save_chain(g, gist, chain):
    """Save the vote chain to Gist or local file"""
    try:
        content = json.dumps(chain, indent=2)
        local_path = os.path.join(BASE_DIR, "vote_chain.json")
        with open(local_path, "w") as f:
            json.dump(chain, f, indent=2)
        if g and gist:
            print(f"Attempting to update Gist with content: {content[:50]}...")  # Debug: Show first 50 chars
            gist.edit(files={GIST_FILENAME: InputFileContent(content)})
            print(f"Gist updated successfully at: {gist.html_url}")
            return gist.html_url
        print(f"Chain saved locally at: {local_path}")
        return local_path
    except Exception as e:
        print(f"Error saving chain to Gist or local file: {e}")
        return None

def merge_chains(local_chain, gist_chain):
    """Merge local and Gist chains, preserving existing hashes unless new block added"""
    if not gist_chain and not local_chain:
        return []
    # Prioritize Gist chain if online, local chain if offline
    base_chain = gist_chain if gist_chain else local_chain
    if not base_chain:
        return []
    # Only merge if the other chain exists and differs
    if local_chain and gist_chain and local_chain != gist_chain:
        combined_chain = gist_chain + [b for b in local_chain if b not in gist_chain]
    else:
        combined_chain = base_chain
    if not combined_chain:
        return []
    seen = set()
    unique_chain = []
    for block in combined_chain:
        key = (block["vote"], block["timestamp"])
        if key not in seen:
            unique_chain.append(block)
            seen.add(key)
    unique_chain = sorted(unique_chain, key=lambda x: x["timestamp"])
    # Preserve existing prev_hash and hash unless new block
    for i in range(1, len(unique_chain)):
        if "prev_hash" not in unique_chain[i] or unique_chain[i]["prev_hash"] != unique_chain[i-1]["hash"]:
            unique_chain[i]["prev_hash"] = unique_chain[i-1]["hash"]
    if unique_chain and unique_chain[0]["prev_hash"] != "genesis_hash":
        unique_chain[0]["prev_hash"] = "genesis_hash"
    return unique_chain

def prune_chain(chain, vote_to_remove):
    """Remove a specific vote and rebuild the chain"""
    if not chain:
        return []
    remaining_chain = [block for block in chain if block["vote"] != vote_to_remove]
    if not remaining_chain:
        return []
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
    chain = load_chain(None)[1]
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

def main():
    # Initialize GitHub client
    g = None
    try:
        if GITHUB_TOKEN:
            g = Github(GITHUB_TOKEN)
            print("GitHub authenticated, running in online mode.")
        else:
            print("No GITHUB_TOKEN, running in offline mode.")
    except Exception as e:
        print(f"GitHub authentication failed: {e}, running in offline mode.")

    # Load existing chains
    gist, gist_chain = load_chain(g) if g else (None, [])
    _, local_chain = load_chain(None)
    chain = merge_chains(local_chain, gist_chain)

    # Sync local chain with Gist if online
    if g and gist:
        chain = sync_local_chain(g, gist, local_chain)

    # Parse stego and verbose flags
    steganography_message = None
    verbose = "--verb" in sys.argv or "--verbose" in sys.argv
    if "--steg" in sys.argv or "--stego" in sys.argv:
        flag = "--steg" if "--steg" in sys.argv else "--stego"
        stego_index = sys.argv.index(flag)
        if stego_index + 1 < len(sys.argv):
            steganography_message = sys.argv[stego_index + 1]
            sys.argv[stego_index:stego_index + 2] = []

    # Parse candidates from command line or positional arguments
    allowed_candidates = []
    if "--candidates" in sys.argv or "--opts" in sys.argv:
        flag = "--candidates" if "--candidates" in sys.argv else "--opts"
        candidates_index = sys.argv.index(flag)
        allowed_candidates = [c for c in sys.argv[candidates_index + 1:] if not c.startswith("--")]
        sys.argv[candidates_index:candidates_index + len(allowed_candidates) + 1] = []
    elif len(sys.argv) > 1 and not any(arg.startswith("--") for arg in sys.argv[1:]):
        allowed_candidates = [c for c in sys.argv[1:] if not c.startswith("--")]
        sys.argv[1:] = []

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
                is_valid, message = validate_chain(chain, verbose)
                if verbose:
                    print(f"New vote added:\n{json.dumps(new_block, indent=2)}")
                if qr_path := create_qr_code(candidate, steganography_message):
                    if verbose:
                        print(f"QR code saved at: {os.path.relpath(qr_path, BASE_DIR)}")
                if verbose:
                    print(f"Updated Chain saved at: {url}")
                print(f"Chain validation: {message}")
        else:
            print("Please provide a QR code filename with --scan, e.g., --scan qrcodes/qr_code_genesis_CandidateA_000001.png")
    elif len(sys.argv) > 1 and sys.argv[1] == "--compare":
        if len(sys.argv) > 2:
            try:
                official_results = json.loads(sys.argv[2])
                compare_with_official(official_results)
            except json.JSONDecodeError:
                print("Invalid official results format. Use JSON, e.g., '{\"CandidateA\": 100, \"CandidateB\": 150}'")
        else:
            print("Please provide official results with --compare, e.g., --compare '{\"CandidateA\": 100, \"CandidateB\": 150}'")
    elif len(sys.argv) > 1 and sys.argv[1] == "--reset":
        reset_chain()
        print("Local chain reset.")
    elif len(sys.argv) > 1 and sys.argv[1] == "--prune":
        if len(sys.argv) > 2:
            vote_to_remove = sys.argv[2]
            chain = prune_chain(chain, vote_to_remove)
            url = save_chain(g, gist, chain)
            is_valid, message = validate_chain(chain, verbose)
            if verbose:
                print(f"Removed vote for {vote_to_remove}")
                print(f"Updated Chain saved at: {url}")
            print(f"Chain validation: {message}")
        else:
            print("Please provide a vote to remove with --prune, e.g., --prune 'Candidate A'")
    else:
        if not allowed_candidates:
            print("No candidates provided. Please run with --candidates flag or provide candidates as positional arguments, e.g., python qrvote.py 'Candidate A' 'Candidate B'")
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
        is_valid, message = validate_chain(chain, verbose)
        if verbose:
            print(f"New vote added:\n{json.dumps(new_block, indent=2)}")
        if qr_path := create_qr_code(vote, steganography_message):
            if verbose:
                print(f"QR code saved at: {os.path.relpath(qr_path, BASE_DIR)}")
        if verbose:
            print(f"Updated Chain saved at: {url}")
        print(f"Chain validation: {message}")

if __name__ == "__main__":
    main()