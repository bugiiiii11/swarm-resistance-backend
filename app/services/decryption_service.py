# services/decryption_service.py - RAW PEM FIX (bypasses all base64 issues)
import base64
import os
import logging
from typing import Dict, Optional
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

logger = logging.getLogger(__name__)

class MedaShooterDecryption:
    """
    Complete RSA decryption service for Unity MedaShooter game
    Handles both score data and game info with separate private keys
    """
    
    def __init__(self):
        self._score_private_key = None
        self._info_private_key = None
        self._load_keys()
        
    def _create_temp_env_file(self):
        """Create PEM files with RAW content (bypassing base64 completely)"""
        
        # Raw PEM content - bypasses all base64/encoding issues
        score_key_pem = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQDV0WK4F2s+m9qKx89vfhxeU5JE9pv8lT23lawVwiq5M6G1N86U
zMLLndtP9R+NTa3LFmtvZ33VApYvzF+9EJ+sVajnmU/2+y3ZCahPPi0mCank1T7b
m3eRMD2tDvMLAY+adHk3nOxtsgVjaYy7R43mmDCUH0dxK35eN3Zbh3uslwIDAQAB
AoGAQ3W1hMl2v6EimWijLNUIFEafvnxkCJP5jeN+ELtbCWWd3nQGDHJx/xYF7Ls0
wjtA2vNu4A4x6DPRuLDtf9Qv2/ZRlFR9hD4ZNQCJpaErzSluzL11HlahZi8AJ8pE
4YBtN7kUCZ7b7OHLJEudGwNr0KXbeog2H5W0ukorHJs0saECQQDWL8XQ2YZSfZ8T
iyJrYgyqJzZPY3RxPUVGTayn1n7Ii3BIIZ6ZaEw806yIXFS8kUMruDkocIBvkD+D
FrXybJwxAkEA/48vzCEaDywFl+MhnvYn4W+pmr7RaJshQbOZBFc5RE+mNr6/LEea
iL5MaCkmZBNn8ADZmZdElGgMEpZcXrpLRwJBALHLokfF6eyb/ur4OjAtinMxhaL
lmNR2ymK3OHN+hx7M0+NKNxraa2sgLIJAwYtBzdJi5j4GoWBllc5CPweEGECQEQI
s3nNaimV15ta3S17bJyIZIeMuyT0/4KFNHxCWD2GUsKKP0yjd1FmD+M+6TiFLgtn
voY0Dg7QMD6Whtq1D6sCQA7R+WHbmFQfBJ1GgXuzezzBo3j01QwUTvoxmZDswqM
/DYMNaTlgMuKoe5iHKQzimey0hRPeTBy31dANpk9h3Q0=
-----END RSA PRIVATE KEY-----"""

        info_key_pem = """-----BEGIN RSA PRIVATE KEY-----
MIICWwIBAAKBgQDQdJersenWQPVT952XkHbsynvkLqzBEe7Cu0y/C7B1kPeQlet0
E2K9SJU0jR1Qs+SlE+q07PrNJ3uMzH+znMzZ5Gm6pTmr9CjDlWlMMP6xirVGG9ca
JF7BffKL1vR6pSXkVYLLjZtVG0g92EAio7vhE9H1hE+h4846zit+LW5GUQIDAQAB
AoGABKXY3OPsZBHSNoNSoPbAZBK2tPWCdhKViYN+GFNlJZXsIy3okE+/V5uW8hNE
aFB+hFy/krWm+OyMsWy82y8flSDVrXtLNipysdBiX4HuAq71LDh2YVvj/Agt9aUx
cOOz4NkZB2mm/M58/H0TQfuApXawIpU7f3UQKPcJ6QxeCu0CQQDcLkn2IHEW9D+S
ts2ucxgmKqzjk1y3CtWFuxtPUBOdNV5AFF+N8294wNV5ZOF+IErLQ+YE5Sl0G4VA
0nI3Bfk1AkEA8l38OtMScLbE59Dz7Gb20NfIirgC6vc4XlryXVFvMjOdFPiaZJWN
hG6fPSHvPhy1tzcpUVzpYYfepM06VwKYLQJAdq7E01S9bsPZmL3MtKH5fPM16h2+
tjOy0LkAiYoCaJUhzqysrRlxFsfqydqk6ZWCe3qH/E+CPsGu3DgTdLEVmQJAUG56
RzdG1lsBK4E/gcOFwzbpGYgJh9p1PXLnHarpwPo59fyumBS9eyaO9+WsFKvIbj4D
Gzo/RRum+oAVDU0SHQJAVKVLAUHRLDW6VVlQOXC5Le8QvSKPAEOgTQJzUnQH5M8N
M3ivwXMQXBZ4yLSY4BqWugTNPeB+hW6TRWxrCbFLAA==
-----END RSA PRIVATE KEY-----"""
        
        # Write RAW PEM content directly to files (no base64 needed)
        try:
            with open("medashooter_score.pem", "w") as f:
                f.write(score_key_pem)
                
            with open("medashooter_info.pem", "w") as f:
                f.write(info_key_pem)
                
            logger.info("✅ RAW PEM key files created successfully (bypassing base64)")
            
        except Exception as e:
            logger.error(f"❌ Failed to create RAW PEM key files: {e}")
            raise
        
    def _load_keys(self):
        """Load RSA private keys directly from PEM files"""
        try:
            # Create PEM files directly (bypassing all base64/environment variable issues)
            self._create_temp_env_file()
            
            # Load from files directly
            score_key_path = "medashooter_score.pem"
            info_key_path = "medashooter_info.pem"
            
            logger.info("🔑 Loading RSA keys directly from PEM files")
            
            with open(score_key_path, 'r') as f:
                score_content = f.read()
                
            with open(info_key_path, 'r') as f:
                info_content = f.read()
                
            logger.info(f"Score key file content starts with: {score_content[:35]}...")
            logger.info(f"Info key file content starts with: {info_content[:35]}...")
            
            # Import RSA keys directly (no base64 decoding needed)
            self._score_private_key = RSA.importKey(score_content)
            self._info_private_key = RSA.importKey(info_content)
            
            logger.info("✅ RSA keys loaded directly from PEM files successfully")
            logger.info(f"Score key: {self._score_private_key.size_in_bits()} bits")
            logger.info(f"Info key: {self._info_private_key.size_in_bits()} bits")
            
        except Exception as e:
            logger.error(f"❌ Failed to load RSA keys: {e}")
            raise Exception(f"RSA key loading failed: {e}")
    
    def decrypt_score_data(self, encrypted_value: str) -> str:
        """
        Decrypt score and address using score private key
        Used for: hash (score) and address parameters
        """
        try:
            cipher = PKCS1_v1_5.new(self._score_private_key)
            encrypted_bytes = base64.b64decode(encrypted_value)
            decrypted = cipher.decrypt(encrypted_bytes, None)
            
            if decrypted is None:
                raise ValueError("Decryption failed - invalid data or wrong key")
                
            return decrypted.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Score data decryption failed: {e}")
            raise ValueError(f"Score decryption error: {e}")
    
    def decrypt_info_data(self, encrypted_value: str) -> str:
        """
        Decrypt game statistics using info private key
        Used for: delta and parameter1-15
        """
        try:
            cipher = PKCS1_v1_5.new(self._info_private_key)
            encrypted_bytes = base64.b64decode(encrypted_value)
            decrypted = cipher.decrypt(encrypted_bytes, None)
            
            if decrypted is None:
                raise ValueError("Decryption failed - invalid data or wrong key")
                
            return decrypted.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Info data decryption failed: {e}")
            raise ValueError(f"Info decryption error: {e}")
    
    def decrypt_score_submission(self, submission: dict) -> dict:
        """
        Decrypt complete Unity score submission
        
        Args:
            submission: Dict containing all 17 encrypted parameters from Unity
            
        Returns:
            Dict with all decrypted game data
        """
        try:
            decrypted_data = {}
            
            # Score and address (using score key)
            decrypted_data["score"] = int(self.decrypt_score_data(submission["hash"]))
            decrypted_data["address"] = self.decrypt_score_data(submission["address"])
            
            # Game statistics (using info key)
            decrypted_data["duration"] = int(self.decrypt_info_data(submission["delta"]))
            decrypted_data["enemies_spawned"] = int(self.decrypt_info_data(submission["parameter1"]))
            decrypted_data["enemies_killed"] = int(self.decrypt_info_data(submission["parameter2"]))
            decrypted_data["waves_completed"] = int(self.decrypt_info_data(submission["parameter3"]))
            decrypted_data["travel_distance"] = int(self.decrypt_info_data(submission["parameter4"]))
            decrypted_data["perks_collected"] = int(self.decrypt_info_data(submission["parameter5"]))
            decrypted_data["coins_collected"] = int(self.decrypt_info_data(submission["parameter6"]))
            decrypted_data["shields_collected"] = int(self.decrypt_info_data(submission["parameter7"]))
            decrypted_data["killing_spree_mult"] = int(self.decrypt_info_data(submission["parameter8"]))
            decrypted_data["killing_spree_duration"] = int(self.decrypt_info_data(submission["parameter9"]))
            decrypted_data["max_killing_spree"] = int(self.decrypt_info_data(submission["parameter10"]))
            
            # Attack speed is stored as integer but should be float (divided by 100)
            attack_speed_raw = int(self.decrypt_info_data(submission["parameter11"]))
            decrypted_data["attack_speed"] = float(attack_speed_raw) / 100.0
            
            decrypted_data["max_score_per_enemy"] = int(self.decrypt_info_data(submission["parameter12"]))
            decrypted_data["max_score_per_enemy_scaled"] = int(self.decrypt_info_data(submission["parameter13"]))
            decrypted_data["ability_use_count"] = int(self.decrypt_info_data(submission["parameter14"]))
            decrypted_data["enemies_killed_while_killing_spree"] = int(self.decrypt_info_data(submission["parameter15"]))
            
            logger.info(f"✅ Successfully decrypted score submission from {decrypted_data['address'][:8]}...")
            return decrypted_data
            
        except Exception as e:
            logger.error(f"❌ Complete decryption failed: {e}")
            raise ValueError(f"Score submission decryption failed: {e}")

# Utility function for Unity's score calculation algorithm
def calculate_shifted_score(raw_score: int) -> int:
    """
    Unity's score calculation algorithm from MedaShooterScore.calculate_score()
    This matches the exact bit manipulation Unity performs
    """
    import numpy as np
    
    score = np.uint32(raw_score)
    score = np.uint32(((score >> 16) ^ score) * 0x119DE1F3)
    score = np.uint32(((score >> 16) ^ score) * 0x119DE1F3)
    return int(np.uint32(((score >> 16) ^ score)))

# Test functions for development
def test_decryption_service():
    """Test the decryption service with mock data"""
    try:
        decryption = MedaShooterDecryption()
        print("✅ Decryption service initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_decryption_service()