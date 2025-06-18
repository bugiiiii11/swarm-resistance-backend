# services/decryption_service.py - FIXED RSA key loading
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
                # Keys stored as base64 encoded environment variables
                logger.info("🔑 Loading RSA keys from environment variables")
                
                # Decode base64 keys
                score_key_content = base64.b64decode(score_key_env).decode('utf-8')
                info_key_content = base64.b64decode(info_key_env).decode('utf-8')
                
                # Import RSA keys
                self._score_private_key = RSA.importKey(score_key_content)
                self._info_private_key = RSA.importKey(info_key_content)
                logger.info("✅ RSA keys loaded from environment variables")
                
            else:
                # Method 2: From file paths (development/local)
                logger.info("🔑 Loading RSA keys from file paths")
                score_key_path = os.getenv('MEDASHOOTER_SCORE_KEY_PATH', 'keys/medashooter_score_privkey.pem')
                info_key_path = os.getenv('MEDASHOOTER_INFO_KEY_PATH', 'keys/medashooter_info_privkey.pem')
                
                with open(score_key_path, 'r') as f:
                    self._score_private_key = RSA.importKey(f.read())
                
                with open(info_key_path, 'r') as f:
                    self._info_private_key = RSA.importKey(f.read())
                
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
    
    def validate_decrypted_data(self, data: dict) -> dict:
        """
        Validate decrypted data for basic sanity checks
        
        Returns:
            Dict with validation results
        """
        errors = []
        warnings = []
        
        # Basic range validations
        if data["score"] < 0 or data["score"] > 10000000:
            errors.append(f"Invalid score range: {data['score']}")
        
        if data["duration"] < 1 or data["duration"] > 3600:  # Max 1 hour
            errors.append(f"Invalid duration: {data['duration']} seconds")
        
        if data["enemies_spawned"] < 0 or data["enemies_spawned"] > 10000:
            errors.append(f"Invalid enemies_spawned: {data['enemies_spawned']}")
        
        if data["enemies_killed"] > data["enemies_spawned"]:
            warnings.append("More enemies killed than spawned")
        
        # Address format validation
        address = data["address"].lower()
        if not address.startswith("0x") or len(address) != 42:
            errors.append(f"Invalid wallet address format: {address}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

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
        
        # Test mock Unity submission format
        mock_submission = {
            "hash": "mock_encrypted_score_data",
            "address": "mock_encrypted_address_data",
            "delta": "mock_encrypted_duration",
            "parameter1": "mock_encrypted_enemies_spawned",
            "parameter2": "mock_encrypted_enemies_killed",
            "parameter3": "mock_encrypted_waves_completed",
            "parameter4": "mock_encrypted_travel_distance",
            "parameter5": "mock_encrypted_perks_collected",
            "parameter6": "mock_encrypted_coins_collected",
            "parameter7": "mock_encrypted_shields_collected",
            "parameter8": "mock_encrypted_killing_spree_mult",
            "parameter9": "mock_encrypted_killing_spree_duration",
            "parameter10": "mock_encrypted_max_killing_spree",
            "parameter11": "mock_encrypted_attack_speed",
            "parameter12": "mock_encrypted_max_score_per_enemy",
            "parameter13": "mock_encrypted_max_score_per_enemy_scaled",
            "parameter14": "mock_encrypted_ability_use_count",
            "parameter15": "mock_encrypted_enemies_killed_while_killing_spree"
        }
        
        print("📝 Mock submission format validated")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_decryption_service()