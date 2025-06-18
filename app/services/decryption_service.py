# services/decryption_service.py - ENHANCED with Unity keys + better base64 handling
import base64
import binascii
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
        
    def _add_base64_padding(self, data: str) -> str:
        """Add proper padding to base64 string if needed"""
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
        return data
        
    def _load_keys(self):
        """Load RSA private keys securely from environment or files"""
        try:
            # Method 1: From environment variables (recommended for production)
            score_key_env = os.getenv('MEDASHOOTER_SCORE_PRIVATE_KEY')
            info_key_env = os.getenv('MEDASHOOTER_INFO_PRIVATE_KEY')
            
            if score_key_env and info_key_env:
                logger.info("🔑 Loading RSA keys from environment variables")
                logger.info(f"Score key length: {len(score_key_env)} chars")
                logger.info(f"Info key length: {len(info_key_env)} chars")
                
                try:
                    # Remove any quotes that Railway might have added
                    score_key_clean = score_key_env.strip().strip('"').strip("'")
                    info_key_clean = info_key_env.strip().strip('"').strip("'")
                    
                    logger.info(f"Cleaned score key length: {len(score_key_clean)} chars")
                    logger.info(f"Score key starts with: {score_key_clean[:20]}...")
                    
                    # Check if it's already PEM format or base64 encoded
                    if score_key_clean.startswith('-----BEGIN'):
                        logger.info("📝 Keys stored as direct PEM content")
                        score_key_content = score_key_clean
                        info_key_content = info_key_clean
                    else:
                        logger.info("🔐 Keys stored as base64 encoded")
                        # Add padding if needed for proper base64 decoding
                        score_key_padded = self._add_base64_padding(score_key_clean)
                        info_key_padded = self._add_base64_padding(info_key_clean)
                        
                        # Decode base64 keys
                        score_key_content = base64.b64decode(score_key_padded).decode('utf-8')
                        info_key_content = base64.b64decode(info_key_padded).decode('utf-8')
                    
                    logger.info(f"Decoded score key starts with: {score_key_content[:30]}...")
                    
                    # Import RSA keys
                    self._score_private_key = RSA.importKey(score_key_content)
                    self._info_private_key = RSA.importKey(info_key_content)
                    
                    logger.info("✅ RSA keys loaded from environment variables")
                    
                except binascii.Error as e:
                    logger.error(f"❌ Base64 decode error: {e}")
                    logger.warning("🔄 Falling back to Unity's hardcoded keys...")
                    self._load_unity_fallback_keys()
                except Exception as e:
                    logger.error(f"❌ RSA import error: {e}")
                    logger.warning("🔄 Falling back to Unity's hardcoded keys...")
                    self._load_unity_fallback_keys()
                
            else:
                # Method 2: From file paths (development/local)
                logger.info("🔑 Attempting to load RSA keys from file paths")
                score_key_path = os.getenv('MEDASHOOTER_SCORE_KEY_PATH', 'keys/medashooter_score_privkey.pem')
                info_key_path = os.getenv('MEDASHOOTER_INFO_KEY_PATH', 'keys/medashooter_info_privkey.pem')
                
                try:
                    with open(score_key_path, 'r') as f:
                        score_content = f.read()
                        self._score_private_key = RSA.importKey(score_content)
                    
                    with open(info_key_path, 'r') as f:
                        info_content = f.read()
                        self._info_private_key = RSA.importKey(info_content)
                    
                    logger.info(f"✅ RSA keys loaded from files: {score_key_path}, {info_key_path}")
                    
                except FileNotFoundError:
                    logger.warning("📁 Key files not found, using Unity's hardcoded keys...")
                    self._load_unity_fallback_keys()
                
            # Validate key sizes
            if self._score_private_key and self._info_private_key:
                logger.info(f"Score key: {self._score_private_key.size_in_bits()} bits")
                logger.info(f"Info key: {self._info_private_key.size_in_bits()} bits")
                logger.info("✅ RSA decryption service initialized successfully")
            else:
                raise Exception("Failed to load any RSA keys")
            
        except Exception as e:
            logger.error(f"❌ Failed to load RSA keys: {e}")
            raise Exception(f"RSA key loading failed: {e}")
    
    def _load_unity_fallback_keys(self):
        """Load Unity's exact hardcoded keys as fallback"""
        logger.info("🔧 Loading Unity's exact hardcoded keys")
        
        # EXACT Unity-provided score private key
        score_key_pem = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQDV0WK4F2s+m9qKx89vfhxeU5JE9pv8lT23lawVwiq5M6G1N86U
zMLLndtP9R+NTa3LFmtvZ33VApYvzF+9EJ+sVajnmU/2+y3ZCahPPi0mCank1T7b
m3eRMD2tDvMLAY+adHk3nOxtsgVjaYy7R43mmDCUH0dxK35eN3Zbh3uslwIDAQAB
AoGAQ3W1hMl2v6EimWijLNUIFEafvnxkCJP5jeN+ELtbCWWd3nQGDHJx/xYF7Ls0
wjtA2vNu4A4x6DPRuLDtf9Qv2/ZRlFR9hD4ZNQCJpaErzSluzL11HlahZi8AJ8pE
4YBtN7kUCZ7b7OHLJEudGwNr0KXbeog2H5W0ukorHJs0saECQQDWL8XQ2YZSfZ8T
iyJrYgyqJzZPY3RxPUVGTayn1n7Ii3BIIZ6ZaEw806yIXFS8kUMruDkocIBvkD+D
FrXybJwxAkEA/48vzCEaDywFl+MhnvYn4W+pmr7RaJshQbOZBFc5RE+mNr6/LEea
iL5MaCkmZBNn8ADZmZdElGgMEpZcXrpLRwJBALHLokfF6eyb/ur4OjAtihnMxxaL
lmNR2ymK3OHN+hx7M0+NKNxraa2sgLIJAwYtBzdJi5j4GoWBllc5CPweEGECQEQI
s3nNaimV15ta3S17bJyIZIeMuyT0/4KFNHxCWD2GUsKKP0yjd1FmD+M+6TiFLgtn
voY0Dg7QMD6Whtq1D6sCQA7R+WHbmFQfBJ1GgXuzezzzBo3j01QwUTvoxmZDswqM
/DYMNaTlgMuKoe5iHKQzimy0hRPeTBy31dANpk9h3Q0=
-----END RSA PRIVATE KEY-----"""

        # EXACT Unity-provided info private key
        info_key_pem = """-----BEGIN RSA PRIVATE KEY-----
MIICWwIBAAKBgQDQdJersenWQPVT952XkHbsynvkLqzBEe7Cu0y/C7B1kPeQlet0
E2K9SJU0jR1Qs+SlE+q07PrNJ3uMzH+znMzZ5Gm6pTmr9CjDlWlMMP6xirVGG9ca
IP7BffKL1vR6pSXkVYLLjZtVG0g92EAio7vhE9H1hEKh4846zit+LW5GUQIDAQAB
AoGABKXY3OPsZBHSNoNSoPbAZBK2tPWCdhKViYN+GFNlJZXsIy3okE+/V5uW8hNE
aFB+hFy/krWm+OyMsWy82y8flSDVrXtLNipysdBiX4HuAq71LDh2YVvj/Agt9aUx
cOOz4NkZB2mm/M58/H0TQfuApXawIpU7f3UQKPcJ6QxeCu0CQQDcLkn2IHEw9D+S
ts2ucxgnKqzjk1y3CtWFuxtPUBOdNV5AFF+N8294wNV5ZOF+IErLQ+YE5Sl0G4VA
0nI3Bfk1AkEA8l38OtMScLbE59Dz7Gb20NfIirgC6vc4XlryXVFvMjOdFPiaZJWN
hG6fPSHvPhy1tzcpUVzpYYfepM06VwKYLQJAdq7E01S9bsPZmL3MtKH5fPM16h2+
tjOy0LkAiYoCaJUhzqysrRlxFsfqydqk6ZWCe3qH/E+CPsGu3DgTtLEVmQJAUG56
RzdG1lsBK4E/gcOFwzbpGYgJh9p1PXLnHarpwPo59fyumBS9eyaO9+WsFKvIbj4D
Gzo/RRum+oAVDU0SHQJAVkVLaUhRLdW6VVlQOXC5Le8QvSKPAEOgTQJzUnQH5M8N
M3ivwXMQXBZ4yLSY4BqWugTNPeB+hW6TRWxrCbFLAA==
-----END RSA PRIVATE KEY-----"""

        self._score_private_key = RSA.importKey(score_key_pem)
        self._info_private_key = RSA.importKey(info_key_pem)
        logger.info("✅ Unity fallback keys loaded successfully")
    
    def is_available(self) -> bool:
        """Check if RSA decryption service is available"""
        return self._score_private_key is not None and self._info_private_key is not None
    
    def decrypt_score_data(self, encrypted_value: str) -> str:
        """
        Decrypt score and address using score private key
        Used for: hash (score) and address parameters
        """
        if not self._score_private_key:
            raise ValueError("Score private key not loaded")
            
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
        if not self._info_private_key:
            raise ValueError("Info private key not loaded")
            
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

# Global instance
_decryption_service = None

def get_decryption_service():
    """Get global decryption service instance"""
    global _decryption_service
    if _decryption_service is None:
        try:
            _decryption_service = MedaShooterDecryption()
        except Exception as e:
            logger.error(f"Failed to initialize decryption service: {e}")
            _decryption_service = None
    return _decryption_service

# Test functions for development
def test_decryption_service():
    """Test the decryption service with mock data"""
    try:
        decryption = MedaShooterDecryption()
        print(f"✅ Decryption service initialized successfully")
        print(f"✅ Service available: {decryption.is_available()}")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_decryption_service()