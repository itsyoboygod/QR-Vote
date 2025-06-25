import unittest
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  # Add src to path
import qrvote

class TestQRVote(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_temp"
        os.makedirs(self.test_dir, exist_ok=True)
        os.chdir(self.test_dir)
        self.chain_file = "vote_chain.json"
        self.qr_dir = "qrcodes"

    def tearDown(self):
        os.chdir("..")
        for file in os.listdir(self.test_dir):
            os.remove(os.path.join(self.test_dir, file))
        os.rmdir(self.test_dir)

    def test_add_vote(self):
        block = qrvote.add_vote("A", "genesis_hash")
        self.assertIn("vote", block)
        self.assertIn("timestamp", block)
        self.assertIn("prev_hash", block)
        self.assertIn("hash", block)
        self.assertEqual(block["prev_hash"], "genesis_hash")

    def test_validate_chain(self):
        chain = [{"election_end_time": "2025-06-25T16:52:00+00:00"},
                 {"vote": "A", "timestamp": "2025-06-25T13:52:00", "prev_hash": "genesis_hash", "hash": qrvote.hash_block({"vote": "A", "timestamp": "2025-06-25T13:52:00", "prev_hash": "genesis_hash"})},
                 {"vote": "B", "timestamp": "2025-06-25T13:53:00", "prev_hash": qrvote.hash_block({"vote": "A", "timestamp": "2025-06-25T13:52:00", "prev_hash": "genesis_hash"}), "hash": qrvote.hash_block({"vote": "B", "timestamp": "2025-06-25T13:53:00", "prev_hash": qrvote.hash_block({"vote": "A", "timestamp": "2025-06-25T13:52:00", "prev_hash": "genesis_hash"})})}
                ]
        is_valid, message = qrvote.validate_chain(chain)
        self.assertTrue(is_valid)
        self.assertEqual(message, "Chain is valid")
        invalid_chain = chain[:-1] + [{"vote": "C", "timestamp": "2025-06-25T13:54:00", "prev_hash": "wrong_hash", "hash": "fake_hash"}]
        is_valid, message = qrvote.validate_chain(invalid_chain)
        self.assertFalse(is_valid)

    def test_create_qr_code(self):
        qr_path = qrvote.create_qr_code("A", verbose=True)
        self.assertTrue(os.path.exists(qr_path))
        qr_path_stego = qrvote.create_qr_code("B", steganography_message="secret", verbose=True)
        self.assertTrue(os.path.exists(qr_path_stego))

    def test_scan_and_vote(self):
        qr_path = qrvote.create_qr_code("A", verbose=True)
        vote = qrvote.scan_and_vote(qr_path, verbose=True)
        self.assertEqual(vote, "A")
        qrvote.ELECTION_END_TIME = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(minutes=1)
        vote = qrvote.scan_and_vote(qr_path, verbose=True)
        self.assertIsNone(vote)

    def test_save_chain(self):
    chain = [{"election_end_time": "2025-06-25T17:04:00+00:00"}, {"vote": "A", "timestamp": "2025-06-25T14:04:00", "prev_hash": "genesis_hash", "hash": qrvote.hash_block({"vote": "A", "timestamp": "2025-06-25T14:04:00", "prev_hash": "genesis_hash"})}]
    url = qrvote.save_chain(None, None, chain, verbose=True)  # Offline mode
    self.assertTrue(os.path.exists(qrvote.os.path.join(self.test_dir, "vote_chain.json")))
    with open(qrvote.os.path.join(self.test_dir, "vote_chain.json"), "r") as f:
        saved_chain = json.load(f)
    self.assertEqual(chain, saved_chain)

if __name__ == '__main__':
    unittest.main()