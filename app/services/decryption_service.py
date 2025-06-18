# services/decryption_service.py - MINIMAL FIX with temporary environment file
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
        """Create temporary file with correct base64 environment variables"""
        
        # The corrected base64 values (these work properly)
        temp_env_content = """MEDASHOOTER_SCORE_PRIVATE_KEY=LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQpNSUlDWEFJQkFBS0JnUURWMFdLNEYycyttOXFLeDg5dmZoeGVVNUpFOXB2OGxUMjNsYXdWd2lxNU02RzFOODZVCnpNTExuZHRQOVIrTlRhM0xGbXR2WjMzVkFwWXZ6Ris5RUorc1Zham5tVS8yK3kzWkNhaFBQaTBtQ2FuazFUN2IKbTNlUk1EMnREdk1MQVkrYWRIazNuT3h0c2dWamFZeTdSNDNtbURDVUgwZHhLMzVlTjNaYmgzdXNsd0lEQVFBQgpBb0dBUTNXMWhNbDJ2NkVpbVdpakxOVUlGRWFmdm54a0NKUDVqZU4rRUx0YkNXV2QzblFHREhKeC94WUY3THMwCndqdEEydk51NEE0eDZEUFJ1TER0ZjlRdjIvWlJsRlI5aEQ0Wk5RQ0pwYUVyelNsdXpMMTFIbGFoWmk4QUo4cEUKNFlCdE43a1VDWjdiN09ITEpFdWRHd05yMEtYYmVvZzJINVcwdWtvckhKczBzYUVDUVFEV0w4WFEyWVpTZlo4VAppeUpyWWd5cUp6WlBZM1J4UFVWR1RheW4xbjdJaTNCSUlaNlphRXc4MDZ5SVhGUzhrVU1ydURrb2NJQnZrRCtECkZyWHliSnd4QWtFQS80OHZ6Q0VhRHl3RmwrTWhudlluNFcrcG1yN1JhSnNoUWJPWkJGYzVSRSttTnI2L0xFZWEKaUw1TWFDa21aQk5uOEFEWm1aZEVsR2dNRXBaY1hycExSd0pCQUxITG9rZkY2ZXliL3VyNE9qQXRpbk14aGFMCmxtTlIyeW1LM09ITitoeDdNMCtOS054cmFhMnNnTElKQXdZdEJ6ZEppNWo0R29XQmxsYzVDUHdlRUdFQ1FFUUkKczNuTmFpbVYxNXRhM1MxN2JKeUlaSWVNdXlUMC80S0ZOSHhDV0QyR1VzS0tQMHlqZDFGbUQrTSs2VGlGTGd0bgp2b1kwRGc3UU1ENldodHExRDZzQ1FBN1IrV0hibUZRZkJKMUdnWHV6ZXp6Qm8zajAxUXdVVHZveG1aRHN3cU0KL0RZTU5hVGxnTXVLb2U1aUhLUXppbWV5MGhSUGVUQnkzMWRBTnBrOWgzUTA9Ci0tLS0tRU5EIFJTQSBQUklWQVRFIEtFWS0tLS0t
MEDASHOOTER_INFO_PRIVATE_KEY=LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQpNSUlDV3dJQkFBS0JnUURRZEplcnNlbldRUFZUOTUyWGtIYnN5bnZrTHF6QkVlN0N1MHkvQzdCMWtQZVFsZXQwCkUySzlTSlUwalIxUXMrU2xFK3EwN1ByTkozdU16SCt6bk16WjVHbTZwVG1yOUNqRGxXbE1NUDZ4aXJWR0c5Y2EKSkY3QmZmS0wxdlI2cFNYa1ZZTExqWnRWRzBnOTJFQWlvN3ZoRTlIMWhFK2g0ODQ2eml0K0xXNUdVUUlEQVFBQgpBb0dBQktYWTNPUHNaQkhTTm9OU29QYkFaQksydFBXQ2RoS1ZpWU4rR0ZObEpaWHNJeTNva0UrL1Y1dVc4aE5FCmFGQitoRnkva3JXbStPeU1zV3k4Mnk4ZmxTRFZyWHRMTmlweXNkQmlYNEh1QXE3MUxEaDJZVnZqL0FndDlhVXgKY09PejROa1pCMm1tL001OC9IMFRRZnVBcFhhd0lwVTdmM1VRS1BjSjZReGVDdTBDUVFEY0xrbjJJSEVXOUQrUwp0czJ1Y3hnbUtxemprMXkzQ3RXRnV4dFBVQk9kTlY1QUZGK044Mjk0d05WNVpPRitJRXJMUStZRTVTbDBHNFZBCjBuSTNCZmsxQWtFQThsMzhPdE1TY0xiRTU5RHo3R2IyME5mSWlyZ0M2dmM0WGxyeVhWRnZNak9kRlBpYVpKV04KaEc2ZlBTSHZQaHkxdHpjcFVWenBZWWZlcE0wNlZ3S1lMUUpBZHE3RTAxUzlic1BabUwzTXRLSDVmUE0xNmgyKwp0ak95MExrQWlZb0NhSlVoenF5c3JSbHhGc2ZxeWRxazZaV0NlM3FIL0UrQ1BzR3UzRGdUZExFVm1RSkFVRzU2ClJ6ZEcxbHNCSzRFL2djT0Z3emJwR1lnSmg5cDFQWExuSGFycHdQbzU5Znl1bUJTOWV5YU85K1dzRkt2SWJqNEQKR3pvL1JSdW0rb0FWRFUwU0hRSkFWS1ZMQVVIUkxEVzZWVmxRT1hDNUxlOFF2U0tQQUVPZ1RRSnpVblFINU04TgpNM2l2d1hNUVhCWjR5TFNZNEJxV3VnVE5QZUIraFc2VFJXeHJDYkZMQUE9PQotLS0tLUVORCBSU0EgUFJJVkFURSBLRVktLS0tLQ=="""
        
        with open(".temp_env", "w") as f:
            f.write(temp_env_content)
        
        logger.info("✅ Temporary environment file created")

    def _read_temp_env_file(self):
        """Read temporary environment file"""
        env_vars = {}
        try:
            with open(".temp_env", "r") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        env_vars[key] = value
            logger.info(f"✅ Read {len(env_vars)} variables from temporary file")
            return env_vars
        except Exception as e:
            logger.error(f"❌ Failed to read temporary environment file: {e}")
            return {}
        
    def _load_keys(self):
        """Load RSA private keys securely from environment or files"""
        try:
            # Create a temporary file with correct base64 values (Railway workaround)
            self._create_temp_env_file()
            
            # Method 1: From temporary file (simulating fixed environment variables)
            temp_env = self._read_temp_env_file()
            score_key_env = temp_env.get('MEDASHOOTER_SCORE_PRIVATE_KEY')
            info_key_env = temp_env.get('MEDASHOOTER_INFO_PRIVATE_KEY')
            
            if score_key_env and info_key_env:
                logger.info("🔑 Loading RSA keys from temporary environment file")
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
                    
                    logger.info("✅ RSA keys loaded from temporary environment file")
                    
                except base64.binascii.Error as e:
                    logger.error(f"❌ Base64 decode error: {e}")
                    raise Exception(f"Base64 decoding failed: {e}")
                except Exception as e:
                    logger.error(f"❌ RSA import error: {e}")
                    raise Exception(f"RSA key import failed: {e}")
                    
            else:
                # Method 2: Fallback to original environment variables
                logger.info("🔄 Falling back to original environment variables")
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
                    # Method 3: From file paths (development/local)
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