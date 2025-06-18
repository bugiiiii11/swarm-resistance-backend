# services/decryption_service.py - FIXED with better RSA key debugging
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
                    
                    # Decode base64 keys
                    score_key_content = base64.b64decode(score_key_clean).decode('utf-8')
                    info_key_content = base64.b64decode(info_key_clean).decode('utf-8')
                    
                    logger.info(f"Decoded score key starts with: {score_key_content[:30]}...")
                    
                    # Import RSA keys
                    self._score_private_key = RSA.importKey(score_key_content)
                    self._info_private_key = RSA.importKey(info_key_content)
                    
                    logger.info("✅ RSA keys loaded from environment variables")
                    
                except base64.binascii.Error as e:
                    logger.error(f"❌ Base64 decode error: {e}")
                    raise Exception(f"Base64 decoding failed: {e}")
                except Exception as e:
                    logger.error(f"❌ RSA import error: {e}")
                    raise Exception(f"RSA key import failed: {e}")
                
            else:
                # Method 2: From file paths (development/local)
                logger.info("🔑 Loading RSA keys from file paths")
                score_key_path = os.getenv('MEDASHOOTER_SCORE_KEY_PATH', 'keys/medashooter_score_privkey.pem')
                info_key_path = os.getenv('MEDASHOOTER_INFO_KEY_PATH', 'keys/medashooter_info_privkey.pem')
                
                with open(score_key_path, 'r') as f:
                    score_content = f.read()
                    self._score_private_key = RSA.importKey(score_content)
                
                with open(info_key_path, 'r') as f:
                    info_content = f.read()
                    self._info_private_key = RSA.importKey(info_content)
                
                logger.info(f"✅ RSA keys loaded from files: {score_key_path}, {info_key_path}")
                
            # Validate key sizes
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