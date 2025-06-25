import json, hashlib, datetime, qrcode, base64, sys, time, re, os
from github import Github, InputFileContent
from pyzbar.pyzbar import decode
from PIL import Image

# Optional: Install pyqrcode for ASCII support if not already installed
try:
    import pyqrcode
    HAS_ASCII = True
except ImportError:
    HAS_ASCII = False

# Configuration
from dotenv import load_dotenv
load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Set base directory to script location
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GIST_FILENAME = os.getenv("GIST_FILENAME", "vote_chain.json")
GIST_DESCRIPTION = os.getenv("GIST_DESCRIPTION", "QR Vote Street Talk Blockchain")

# Election end time will be set dynamically for genesis vote
ELECTION_END_TIME = None

# Try to import stegano for steganography, fall back if unavailable
try:
    from stegano import lsb
    HAS_STEGANOGRAPHY = True
except ImportError:
    HAS_STEGANOGRAPHY = False

def parse_election_end_time(elec_input):
    """Parse election end time from --elec flag input."""
    global ELECTION_END_TIME
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    
    # Check for relative time (e.g., "240min", "4h", "2d")
    match = re.match(r'^(\d+)(min|h|d)$', elec_input.strip().lower())
    if match:
        value, unit = int(match.group(1)), match.group(2)
        if unit == 'min':
            delta = datetime.timedelta(minutes=value)
        elif unit == 'h':
            delta = datetime.timedelta(hours=value)
        elif unit == 'd':
            delta = datetime.timedelta(days=value)
        ELECTION_END_TIME = now + delta
        return True
    
    # Check for absolute time (e.g., "2025-06-15 18:00:00+00:00")
    try:
        ELECTION_END_TIME = datetime.datetime.fromisoformat(elec_input.replace(' ', 'T')).replace(tzinfo=datetime.timezone.utc)
        if ELECTION_END_TIME <= now:
            print("Error: Election end time must be in the future.")
            return False
        return True
    except ValueError:
        print("Error: Invalid time format. Use '240min', '4h', '2d', or 'YYYY-MM-DD HH:MM:SS+00:00'.")
        return False

def log_verbose(msg, verbose=False):
    """Log message with timestamp only in verbose mode."""
    if verbose:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")
    else:
        print(msg)

def show_loading(duration=2, message="Processing..."):
    """Display a simple loading animation in the terminal."""
    animation = ["|", "/", "-", "\\"]
    start_time = time.time()
    while time.time() - start_time < duration:
        for frame in animation:
            sys.stdout.write(f"\r{message} {frame}")
            sys.stdout.flush()
            time.sleep(0.2)
    sys.stdout.write("\r" + " " * 50 + "\r")  # Clear the line
    sys.stdout.flush()

def hash_block(block):
    """Calculate SHA-256 hash of a block"""
    block_string = json.dumps(block, sort_keys=True).encode()
    return hashlib.sha256(block_string).hexdigest()

def load_chain(g, verbose=False):
    """Load the vote chain from Gist or local file and set ELECTION_END_TIME if present"""
    global ELECTION_END_TIME
    try:
        if g:
            user = g.get_user()
            for gist in user.get_gists():
                if GIST_FILENAME in gist.files:
                    content = gist.files[GIST_FILENAME].content
                    chain = json.loads(content) if content else []
                    if chain and "election_end_time" in chain[0]:
                        ELECTION_END_TIME = datetime.datetime.fromisoformat(chain[0]["election_end_time"]).replace(tzinfo=datetime.timezone.utc)
                    return gist, chain
        local_path = os.path.join(BASE_DIR, "vote_chain.json")
        if os.path.exists(local_path):
            with open(local_path, "r") as f:
                content = f.read().strip()
                chain = json.loads(content) if content else []
                if chain and "election_end_time" in chain[0]:
                    ELECTION_END_TIME = datetime.datetime.fromisoformat(chain[0]["election_end_time"]).replace(tzinfo=datetime.timezone.utc)
                return None, chain
        return None, []
    except Exception as e:
        log_verbose(f"Error loading chain: {e}", verbose)
        return None, []

def sync_local_chain(g, gist, local_chain, verbose=False):
    """Sync local vote_chain.json with the latest Gist data, merging with local changes"""
    if g and gist:
        try:
            show_loading(message="Syncing with Gist...")
            content = gist.files[GIST_FILENAME].content
            gist_chain = json.loads(content) if content else []
            merged_chain = merge_chains(local_chain, gist_chain)
            local_path = os.path.join(BASE_DIR, "vote_chain.json")
            with open(local_path, "w") as f:
                json.dump(merged_chain, f, indent=2)
            log_verbose(f"Local chain synced with Gist. Blocks: {len(merged_chain)}, First hash: {merged_chain[1]['hash'] if len(merged_chain) > 1 else 'N/A'}", verbose)
            return merged_chain
        except Exception as e:
            log_verbose(f"Error syncing local chain: {e}", verbose)
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

def create_qr_code(candidate, steganography_message=None, verbose=False):
    try:
        show_loading(message="Generating QR code...")
        qr_data = f"genesis:{candidate}"
        qr = qrcode.QRCode(
            version=2,
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
        
        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_image.save(qr_path)
        log_verbose(f"QR code generated at: {qr_path}", verbose)

        if HAS_STEGANOGRAPHY and steganography_message:
            qr_image_rgb = qr_image.convert("RGB")
            qr_image_rgb.save(qr_path)
            MIN_LENGTH = 1
            MAX_LENGTH = 100
            if not (MIN_LENGTH <= len(steganography_message) <= MAX_LENGTH):
                return qr_path
            show_loading(message="Embedding steganography...")
            # Create stego file discreetly without announcing
            stego_path = os.path.join(qr_dir, f"stego_{qr_filename}")
            secret_image = lsb.hide(qr_path, steganography_message)
            secret_image.save(stego_path)
            # Return original QR path to avoid mentioning stego
            return qr_path
        return qr_path
    except Exception as e:
        log_verbose(f"Error generating QR code or steganography: {e}", verbose)
        return None

def create_ascii_qr_code(candidate, verbose=False):
    if not HAS_ASCII:
        log_verbose("ASCII QR code generation requires 'pyqrcode' library. Please install it with 'pip install pyqrcode'", verbose)
        return None
    try:
        show_loading(message="Generating ASCII QR code...")
        qr_data = f"genesis:{candidate}"
        qr = pyqrcode.create(qr_data, error='H', version=2)
        ascii_art = qr.terminal(module_color=0, background=7, quiet_zone=1)
        ascii_filename = f"qr_code_genesis_{candidate.replace(' ', '_')}_000001.txt"
        ascii_path = os.path.join(BASE_DIR, "qrcodes", ascii_filename)
        qr_dir = os.path.join(BASE_DIR, "qrcodes")
        os.makedirs(qr_dir, exist_ok=True)
        with open(ascii_path, "w") as f:
            f.write(ascii_art)
        log_verbose(f"ASCII QR code saved at: {ascii_path}", verbose)
        return ascii_path
    except Exception as e:
        log_verbose(f"Error generating ASCII QR code: {e}", verbose)
        return None

def scan_and_vote(qr_filename, verbose=False):
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
            if ELECTION_END_TIME and current_time > ELECTION_END_TIME:
                print(f"Election ended at {ELECTION_END_TIME}. No further votes accepted.")
                return None
            return candidate
        return None
    except Exception as e:
        log_verbose(f"Error scanning QR code: {e}", verbose)
        return None

def validate_chain(chain, verbose=False):
    """Validate the vote chain with optional verbose output, skipping metadata block"""
    try:
        if not chain or len(chain) < 2:  # No votes to validate if only metadata
            return True, "Chain is valid (no votes yet)"
        vote_blocks = [block for block in chain[1:] if "vote" in block]  # Only validate blocks with vote
        if not vote_blocks:
            return True, "Chain is valid (no vote blocks)"
        for i, block in enumerate(vote_blocks[1:], 1):  # Validate from second vote block
            prev_block = vote_blocks[i-1]
            if block["prev_hash"] != prev_block["hash"]:
                if verbose:
                    log_verbose(f"Validation failed at block {i+1}: prev_hash {block['prev_hash']} != {prev_block['hash']}", verbose)
                return False, f"Invalid previous hash at block {i+1}"
            block_copy = block.copy()
            current_hash = block_copy.pop("hash")
            calculated_hash = hash_block(block_copy)
            if current_hash != calculated_hash:
                if verbose:
                    log_verbose(f"Validation failed at block {i+1}: stored hash {current_hash} != calculated {calculated_hash}", verbose)
                return False, f"Invalid hash at block {i+1}"
        # Validate the first vote block's prev_hash against genesis_hash
        if vote_blocks[0]["prev_hash"] != "genesis_hash":
            if verbose:
                log_verbose(f"Validation failed at block 1: prev_hash {vote_blocks[0]['prev_hash']} != genesis_hash", verbose)
            return False, "Invalid genesis hash at block 1"
        return True, "Chain is valid"
    except Exception as e:
        if verbose:
            log_verbose(f"Validation error: {e}", verbose)
        return False, "Validation error"

def save_chain(g, gist, chain, verbose=False):
    """Save the vote chain to Gist or local file"""
    try:
        content = json.dumps(chain, indent=2)
        local_path = os.path.join(BASE_DIR, "vote_chain.json")
        with open(local_path, "w") as f:
            json.dump(chain, f, indent=2)
        if g and gist:
            show_loading(message="Updating Gist...")
            log_verbose(f"Attempting to update Gist with content: {content[:50]}...", verbose)
            gist.edit(files={GIST_FILENAME: InputFileContent(content)})
            log_verbose(f"Gist updated successfully at: {gist.html_url}", verbose)
            return gist.html_url
        log_verbose(f"Chain saved locally at: {local_path}", verbose)
        return local_path
    except Exception as e:
        log_verbose(f"Error saving chain to Gist or local file: {e}", verbose)
        return None

def merge_chains(local_chain, gist_chain):
    """Merge local and Gist chains, preserving existing hashes and metadata block"""
    if not gist_chain and not local_chain:
        return []
    base_chain = gist_chain if gist_chain else local_chain
    if not base_chain:
        return []
    
    # Preserve metadata block if present
    metadata = None
    if base_chain and "election_end_time" in base_chain[0]:
        metadata = base_chain[0]
        base_chain = base_chain[1:]
    
    if local_chain and gist_chain and local_chain != gist_chain:
        combined_chain = gist_chain[1:] + [b for b in local_chain[1:] if b not in gist_chain[1:]]
    else:
        combined_chain = base_chain
    
    if not combined_chain:
        return [metadata] if metadata else []
    
    seen = set()
    unique_chain = []
    for block in combined_chain:
        if "vote" in block:  # Only consider blocks with vote data
            key = (block["vote"], block["timestamp"])
            if key not in seen:
                unique_chain.append(block)
                seen.add(key)
    
    unique_chain = sorted(unique_chain, key=lambda x: x["timestamp"])
    for i in range(1, len(unique_chain)):
        if "prev_hash" not in unique_chain[i] or unique_chain[i]["prev_hash"] != unique_chain[i-1]["hash"]:
            unique_chain[i]["prev_hash"] = unique_chain[i-1]["hash"]
    if unique_chain and unique_chain[0]["prev_hash"] != "genesis_hash":
        unique_chain[0]["prev_hash"] = "genesis_hash"
    
    return [metadata] + unique_chain if metadata else unique_chain

def prune_chain(chain, vote_to_remove):
    """Remove a specific vote and rebuild the chain"""
    if not chain or len(chain) < 2:  # Skip metadata block
        return chain
    remaining_chain = [chain[0]] + [block for block in chain[1:] if block["vote"] != vote_to_remove]
    if len(remaining_chain) <= 1:
        return remaining_chain
    for i in range(1, len(remaining_chain)):
        remaining_chain[i]["prev_hash"] = remaining_chain[i-1]["hash"]
        remaining_chain[i]["hash"] = hash_block(remaining_chain[i])
    return remaining_chain

def get_vote_counts(chain):
    """Calculate vote counts per candidate"""
    counts = {}
    for block in chain[1:]:  # Skip metadata block
        if "vote" in block:
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
    # Declare and initialize verbose at the start
    global verbose
    verbose = False  # Default to False
    verbose = "--verb" in sys.argv or "--verbose" in sys.argv

    # Initialize GitHub client
    g = None
    try:
        if GITHUB_TOKEN:
            g = Github(GITHUB_TOKEN)
            log_verbose("GitHub authenticated, running in online mode.", verbose)
        else:
            log_verbose("No GITHUB_TOKEN, running in offline mode.", verbose)
    except Exception as e:
        log_verbose(f"GitHub authentication failed: {e}, running in offline mode.", verbose)

    # Load existing chains
    gist, gist_chain = load_chain(g, verbose) if g else (None, [])
    _, local_chain = load_chain(None, verbose)
    chain = merge_chains(local_chain, gist_chain)
    log_verbose(f"Initial chain loaded. Blocks: {len(chain)}, First hash: {chain[1]['hash'] if len(chain) > 1 else 'N/A'}", verbose)

    # Sync local chain with Gist if online
    if g and gist:
        chain = sync_local_chain(g, gist, local_chain, verbose)

    # Parse stego, ascii, and verbose flags
    steganography_message = None
    ascii_mode = "--ascii" in sys.argv
    if "--steg" in sys.argv or "--stego" in sys.argv:
        flag = "--steg" if "--steg" in sys.argv else "--stego"
        stego_index = sys.argv.index(flag)
        if stego_index + 1 < len(sys.argv):
            steganography_message = sys.argv[stego_index + 1]
            sys.argv[stego_index:stego_index + 2] = []

    # Parse election end time for genesis vote
    global ELECTION_END_TIME
    if len(chain) <= 1 and "--elec" not in sys.argv:  # Allow for metadata block
        print("Error: Genesis vote requires --elec flag to set election end time (e.g., '240min' or '2025-06-15 18:00:00+00:00').")
        return
    if "--elec" in sys.argv:
        elec_index = sys.argv.index("--elec")
        if elec_index + 1 < len(sys.argv):
            elec_input = sys.argv[elec_index + 1]
            if not parse_election_end_time(elec_input):
                return
            # Add election end time to the first block for persistence
            if len(chain) <= 1 and (not chain or "election_end_time" not in chain[0]):
                chain.insert(0, {"election_end_time": ELECTION_END_TIME.isoformat()})
            sys.argv[elec_index:elec_index + 2] = []
        else:
            print("Error: --elec requires a time value (e.g., '240min' or '2025-06-15 18:00:00+00:00').")
            return

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
            candidate = scan_and_vote(qr_filename, verbose)
            if candidate:
                prev_hash = chain[-1]["hash"] if chain and len(chain) > 1 and "hash" in chain[-1] else "genesis_hash"
                new_block = add_vote(candidate, prev_hash)
                chain.append(new_block)
                url = save_chain(g, gist, chain, verbose)
                is_valid, message = validate_chain(chain, verbose)
                if verbose:
                    log_verbose(f"New vote added:\n{json.dumps(new_block, indent=2)}", verbose)
                if ascii_mode:
                    if ascii_path := create_ascii_qr_code(candidate, verbose):
                        if verbose:
                            log_verbose(f"ASCII QR code saved at: {os.path.relpath(ascii_path, BASE_DIR)}", verbose)
                else:
                    if qr_path := create_qr_code(candidate, steganography_message, verbose):
                        if verbose:
                            log_verbose(f"QR code saved at: {os.path.relpath(qr_path, BASE_DIR)}", verbose)
                if verbose:
                    log_verbose(f"Updated Chain saved at: {url}", verbose)
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
        log_verbose("Local chain reset.", verbose)
    elif len(sys.argv) > 1 and sys.argv[1] == "--prune":
        if len(sys.argv) > 2:
            vote_to_remove = sys.argv[2]
            chain = prune_chain(chain, vote_to_remove)
            url = save_chain(g, gist, chain, verbose)
            is_valid, message = validate_chain(chain, verbose)
            if verbose:
                log_verbose(f"Removed vote for {vote_to_remove}", verbose)
                log_verbose(f"Updated Chain saved at: {url}", verbose)
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
        prev_hash = chain[-1]["hash"] if chain and len(chain) > 1 and "hash" in chain[-1] else "genesis_hash"
        new_block = add_vote(vote, prev_hash)
        chain.append(new_block)
        url = save_chain(g, gist, chain, verbose)
        is_valid, message = validate_chain(chain, verbose)
        if verbose:
            log_verbose(f"New vote added:\n{json.dumps(new_block, indent=2)}", verbose)
        if ascii_mode:
            if ascii_path := create_ascii_qr_code(vote, verbose):
                if verbose:
                    log_verbose(f"ASCII QR code saved at: {os.path.relpath(ascii_path, BASE_DIR)}", verbose)
        else:
            if qr_path := create_qr_code(vote, steganography_message, verbose):
                if verbose:
                    log_verbose(f"QR code saved at: {os.path.relpath(qr_path, BASE_DIR)}", verbose)
        if verbose:
            log_verbose(f"Updated Chain saved at: {url}", verbose)
        print(f"Chain validation: {message}")

if __name__ == "__main__":
    main()